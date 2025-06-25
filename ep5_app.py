import streamlit as st
import pdfplumber
import re
from datetime import date, timedelta, time, datetime 
import pandas as pd 
import os

# Ce module analyse les fichiers EP5, calcule les rotations, les indemnités,
# et retourne toutes les données prêtes à être affichées.

BASES_FR = ["CDG", "ORY"]

# --- Fonctions utilitaires (chargement de données, calculs spécifiques) ---

@st.cache_data 
def load_airport_data_from_csv(csv_filepath):
    """Charge les données des aéroports depuis un fichier CSV."""
    airport_data_dict = {}
    try:
        df = pd.read_csv(csv_filepath, delimiter=';', dtype=str, keep_default_na=False)
        required_cols = ['iata_code', 'municipality', 'iso_country', 'name']
        if any(col not in df.columns for col in required_cols):
            return {}
        for _, row in df.iterrows():
            iata = str(row.get('iata_code', '')).strip().upper()
            if iata:
                airport_data_dict[iata] = {
                    "ville": str(row.get('municipality', 'N/A')).strip(),
                    "pays": str(row.get('iso_country', 'N/A')).strip(),
                    "nom_aeroport": str(row.get('name', 'N/A')).strip()
                }
    except Exception:
        # En cas d'échec, on continue silencieusement pour utiliser les données de secours
        pass
    return airport_data_dict

# On tente de charger les données complètes, sinon on utilise un jeu de données minimal
AIRPORT_DATA = load_airport_data_from_csv("airport-codes.csv")
if not AIRPORT_DATA:
    AIRPORT_DATA = { 
        "CDG": {"ville": "Paris", "pays": "FR"}, "ORY": {"ville": "Paris", "pays": "FR"},
        "JFK": {"ville": "New York", "pays": "US"}, "EWR": {"ville": "New York", "pays": "US"},
        "YUL": {"ville": "Montreal", "pays": "CA"}, "LFW": {"ville": "Lome", "pays": "TG"},
        # Ajoutez d'autres aéroports fréquemment utilisés si nécessaire
    }

def get_dgfip_code_for_escale(iata_code, ville, pays_iso):
    """Retourne le code DGFIP spécifique pour certaines localités."""
    if pays_iso == "JP" and ville == "Tokyo": return "TY"
    if iata_code == 'EWR' or (pays_iso == "US" and ville == "New York"): return "NY"
    if iata_code in ['YTZ', 'YKZ', 'YYZ']: return "VT"
    if iata_code in ['CXH', 'YVR']: return "VV"
    if iata_code == 'LFW': return "VL"
    if iata_code in ["ABV", "LOS", "PHC"]: return "NV"
    return pays_iso

@st.cache_data 
def load_indemnity_data(annee_str):
    """Charge les données d'indemnités pour une année donnée."""
    nom_fichier = f"dgfip_indemnites_{annee_str}.csv"
    if not os.path.exists(nom_fichier):
        return {}, f"Fichier d'indemnités introuvable pour {annee_str}: {nom_fichier}"
    
    indemnities_data = {}
    try:
        df = pd.read_csv(nom_fichier, delimiter=';')
        for _, row in df.iterrows():
            code_dgfip = str(row["Code Pays"]).strip().upper()
            date_validite = datetime.strptime(str(row["Date Validité Barème"]).strip(), "%Y-%m-%d").date()
            montant_eur = float(str(row["Montant Barème (EUR)"]).strip())
            if code_dgfip not in indemnities_data: indemnities_data[code_dgfip] = []
            indemnities_data[code_dgfip].append({"date_validite": date_validite, "montant_eur": montant_eur})
        for code in indemnities_data:
            indemnities_data[code].sort(key=lambda x: x["date_validite"], reverse=True)
        return indemnities_data, f"Indemnités pour {annee_str} chargées."
    except Exception as e:
        return {}, f"Erreur de lecture du fichier d'indemnités pour {annee_str}: {e}"

def find_applicable_indemnity(code_dgfip, target_date, indemnity_data):
    """Trouve le montant de l'indemnité applicable à une date donnée."""
    if not indemnity_data or code_dgfip not in indemnity_data: return 0.0
    for bareme in indemnity_data[code_dgfip]:
        if bareme["date_validite"] <= target_date:
            return bareme["montant_eur"]
    return 0.0

def convertir_ep5_heure_en_objet_temps(heure_ep5_str):
    """Convertit l'heure au format EP5 (ex: 9.53) en tuple (h, m)."""
    try:
        if '.' in heure_ep5_str:
            h_str, c_str = heure_ep5_str.split('.', 1)
            minutes = int(float(f"0.{c_str.ljust(2, '0')}") * 60)
            return (int(h_str), minutes)
        return (int(heure_ep5_str), 0)
    except (ValueError, TypeError):
        return (0, 0)

def calculer_date_segment(jour_str, ref_annee, ref_mois, date_depart_ref=None):
    """Calcule la date correcte d'un segment, en gérant les changements de mois."""
    try:
        jour = int(jour_str)
        annee, mois = (date_depart_ref.year, date_depart_ref.month) if date_depart_ref else (ref_annee, ref_mois)
        if date_depart_ref and jour < date_depart_ref.day:
            mois += 1
            if mois > 12:
                mois = 1
                annee += 1
        return date(annee, mois, jour)
    except (ValueError, TypeError):
        return None

pattern_ep5_line = re.compile(
    r"^\s*\d+\s+"
    r"([A-Z0-9-]+)\s+"      # Type Avion (ex: B777-300ER)
    r"([A-Z0-9]+)\s+"       # Immatriculation (ex: FGSQI)
    r"([A-Z0-9]+)\s+"       # Numéro de vol
    r"([A-Z]{3})\s+"        # Aéroport Départ
    r"(\d{1,2})\s*\|\s*"    # Jour Départ
    r"(\d{1,2}\.?\d{0,3})\s+" # Heure Départ (ex: 9.53 ou 10)
    r"([A-Z]{3})\s+"        # Aéroport Arrivée
    r"(\d{1,2})\s*\|\s*"    # Jour Arrivée
    r"(\d{1,2}\.?\d{0,3})"   # Heure Arrivée
)

def analyser_page_ep5(texte_page, annee_base, mois_base, nom_fichier):
    """Extrait les segments de vol et reconstitue les rotations d'une page de PDF."""
    segments = []
    for ligne in texte_page.split('\n'):
        match = pattern_ep5_line.search(ligne.strip())
        if match:
            try:
                date_dep = calculer_date_segment(match.group(5), annee_base, mois_base)
                if not date_dep: continue
                date_arr = calculer_date_segment(match.group(8), annee_base, mois_base, date_depart_ref=date_dep)
                if not date_arr: continue
                
                segments.append({
                    'avion_type': match.group(1), 'avion_immat': match.group(2),
                    'dep_airport': match.group(4), 'dep_date': date_dep,
                    'arr_airport': match.group(7), 'arr_date': date_arr,
                    'nom_fichier': nom_fichier
                })
            except Exception:
                continue
    segments.sort(key=lambda s: s['dep_date'])
    
    rotations, rotation_en_cours = [], []
    for seg in segments:
        rotation_en_cours.append(seg)
        if seg['arr_airport'] in BASES_FR:
            if rotation_en_cours[0]['dep_airport'] in BASES_FR:
                rotations.append(list(rotation_en_cours))
            rotation_en_cours = []
    return rotations

# --- Fonction principale du module ---

def analyse_missions(uploaded_files):
    """
    Fonction principale qui orchestre l'analyse des fichiers EP5.
    Retourne un dictionnaire de résultats pour l'affichage centralisé.
    """
    toutes_rotations_brutes = []
    indemnity_data_par_annee = {}
    warnings = []

    for f in uploaded_files:
        # Logique d'extraction de la date du fichier (simplifiée pour l'exemple)
        match_date = re.search(r"(\d{2})[_-]?(\d{4})", f.name) # MM-YYYY
        if not match_date:
            warnings.append(f"Format de date non reconnu dans '{f.name}'.")
            continue
        
        mois_base, annee_base = int(match_date.group(1)), int(match_date.group(2))
        annee_str = str(annee_base)

        if annee_str not in indemnity_data_par_annee:
            data, msg = load_indemnity_data(annee_str)
            indemnity_data_par_annee[annee_str] = data
            warnings.append(msg)
        
        try:
            with pdfplumber.open(f) as pdf:
                for page in pdf.pages:
                    texte = page.extract_text() or ""
                    if "EP5" in texte.upper():
                        rotations_page = analyser_page_ep5(texte, annee_base, mois_base, f.name)
                        for rot in rotations_page:
                            for seg in rot:
                                seg["Année_PDF"] = annee_str
                        toutes_rotations_brutes.extend(rotations_page)
        except Exception as e:
            warnings.append(f"Erreur d'analyse du PDF {f.name}: {e}")

    if not toutes_rotations_brutes:
        return {"has_results": False, "warnings": warnings}

    # Traitement et dédoublonnage des rotations
    rotations_uniques, vus = [], set()
    for rot in toutes_rotations_brutes:
        id_rot = (rot[0]['dep_date'], rot[-1]['arr_date'], rot[0]['dep_airport'], rot[-1]['arr_airport'])
        if id_rot not in vus:
            rotations_uniques.append(rot)
            vus.add(id_rot)
    rotations_uniques.sort(key=lambda r: r[0]['dep_date'])

    # --- Calcul des indemnités et préparation du DataFrame ---
    donnees_tableau = []
    total_indemnites_general = 0.0
    all_segments = [seg for rot in rotations_uniques for seg in rot]

    for rot in rotations_uniques:
        # --- LOGIQUE DE CALCUL RESTAURÉE ---
        date_depart = rot[0]['dep_date']
        date_retour = rot[-1]['arr_date']
        duree = (date_retour - date_depart).days + 1
        annee_rot = rot[0].get("Année_PDF")
        
        itineraire_aeroports = [rot[0]['dep_airport']] + [s['arr_airport'] for s in rot]
        itineraire_str = " → ".join(dict.fromkeys(itineraire_aeroports)) # Dédoublonne les escales consécutives
        
        indemnity_data_annee = indemnity_data_par_annee.get(annee_rot, {})
        
        # Trouver l'escale principale
        escale_principale_iata = None
        if len(itineraire_aeroports) > 1 and itineraire_aeroports[0] in BASES_FR:
            escales_hors_base = [a for a in itineraire_aeroports if a not in BASES_FR]
            if escales_hors_base:
                escale_principale_iata = escales_hors_base[0]

        total_indemnites_rotation = 0.0
        indemnite_journaliere = 0.0
        escale_affichage = "En base / Vol local"

        if escale_principale_iata and indemnity_data_annee and AIRPORT_DATA:
            airport_info = AIRPORT_DATA.get(escale_principale_iata, {})
            if airport_info:
                pays = airport_info.get("pays")
                ville = airport_info.get("ville")
                code_recherche = get_dgfip_code_for_escale(escale_principale_iata, ville, pays)
                indemnite_journaliere = find_applicable_indemnity(code_recherche, date_depart, indemnity_data_annee)
                total_indemnites_rotation = indemnite_journaliere * duree
                escale_affichage = f"{ville} ({pays})"

        donnees_tableau.append({
            "Mois Départ": date_depart.strftime("%B %Y"),
            "Jour Dép.": date_depart.day, "Jour Ret.": date_retour.day,
            "Itinéraire Global": itineraire_str, "Escale Principale": escale_affichage,
            "Indemnité/jour Réf. (EUR)": f"{indemnite_journaliere:.2f}",
            "Durée (j)": duree, "Indemnité Tot. (EUR)": f"{total_indemnites_rotation:.2f}"
        })
        total_indemnites_general += total_indemnites_rotation

    df_rotations = pd.DataFrame(donnees_tableau)
    
    # Stats avions
    df_types, df_immats = pd.DataFrame(), pd.DataFrame()
    if all_segments:
        df_types = pd.DataFrame(pd.Series(s['avion_type'] for s in all_segments).value_counts()).reset_index().rename(columns={'index': 'Type Avion', 0: 'Nombre de Segments'})
        df_immats = pd.DataFrame(pd.Series(s['avion_immat'] for s in all_segments).value_counts()).reset_index().rename(columns={'index': 'Immatriculation', 0: 'Nombre de Segments'})

    annee_predom = max([r[0].get("Année_PDF", "N/A") for r in rotations_uniques], default="N/A")

    return {
        "has_results": True,
        "rotations_df": df_rotations,
        "stats_avions_type_df": df_types,
        "stats_avions_immat_df": df_immats,
        "total_indemnites": total_indemnites_general,
        "annee_predominante": annee_predom,
        "warnings": warnings,
    }
