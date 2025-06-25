import streamlit as st
import pdfplumber
import re
from datetime import date, timedelta, time, datetime 
import pandas as pd 
import os

# --- (Toutes les fonctions de chargement et de calcul initiales restent les mêmes) ---
BASES_FR = ["CDG", "ORY"]

# NOTE: Les fonctions load_airport_data_from_csv, get_dgfip_code_for_escale, 
# load_indemnity_data, find_applicable_indemnity, etc. restent inchangées.
# Par souci de clarté, je ne les répète pas ici. Assurez-vous qu'elles
# sont bien présentes dans votre fichier.

# ... (Collez ici toutes les fonctions de votre fichier ep5_app.py depuis BASES_FR jusqu'à la ligne avant "def analyse_missions(uploaded_files):")
@st.cache_data 
def load_airport_data_from_csv(csv_filepath):
    airport_data_dict = {}
    try:
        df = pd.read_csv(csv_filepath, delimiter=';', dtype=str, keep_default_na=False)
        required_cols = ['iata_code', 'municipality', 'iso_country', 'name'] 
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"Colonnes manquantes dans '{csv_filepath}': {', '.join(missing_cols)}")
            return {} 
        for index, row in df.iterrows():
            iata_raw = row.get('iata_code', ''); ville_raw = row.get('municipality', ''); 
            pays_iso_raw = row.get('iso_country', ''); nom_aeroport_raw = row.get('name', '')
            iata_cleaned = str(iata_raw).strip().upper()
            if iata_cleaned: 
                ville_val = str(ville_raw).strip() if str(ville_raw).strip() else "N/A"
                pays_val = str(pays_iso_raw).strip() if str(pays_iso_raw).strip() else "N/A"
                nom_aeroport_val = str(nom_aeroport_raw).strip() if str(nom_aeroport_raw).strip() else "N/A"
                airport_data_dict[iata_cleaned] = {
                    "ville": ville_val, 
                    "pays": pays_val,
                    "nom_aeroport": nom_aeroport_val
                }
    except FileNotFoundError:
        # Streamlit n'est pas utilisé dans cette fonction, mais on garde l'erreur pour le debug
        print(f"Fichier aéroport '{csv_filepath}' introuvable.")
    except Exception as e:
        print(f"Erreur chargement CSV aéroport '{csv_filepath}': {e}")
    return airport_data_dict

CHEMIN_CSV_AIRPORTS_DRIVE = "airport-codes.csv" 
AIRPORT_DATA = load_airport_data_from_csv(CHEMIN_CSV_AIRPORTS_DRIVE)
# ... etc, toutes vos fonctions ...

def get_dgfip_code_for_escale(iata_code, ville, pays_iso):
    tax_code = pays_iso 
    if pays_iso == "JP" and ville == "Tokyo": tax_code = "TY"
    elif iata_code == 'EWR' or (pays_iso == "US" and ville == "New York"): tax_code = "NY"
    elif iata_code in ['YTZ', 'YKZ', 'YYZ']: tax_code = "VT"
    elif iata_code in ['CXH', 'YVR']: tax_code = "VV"
    elif iata_code == 'LFW': tax_code = "VL"
    elif iata_code in ["ABV", "LOS", "PHC"]: tax_code = "NV"
    return tax_code

@st.cache_data 
def load_indemnity_data(annee_str):
    nom_fichier_indemnites = f"dgfip_indemnites_{annee_str}.csv"
    # La logique de recherche de fichier reste la même.
    # Les messages st.warning/st.error seront remplacés par des retours de warnings.
    chemin_fichier_indemnites = nom_fichier_indemnites
    if not os.path.exists(chemin_fichier_indemnites):
        chemin_fichier_indemnites = f"../{nom_fichier_indemnites}"
        if not os.path.exists(chemin_fichier_indemnites):
            return {}, f"Fichier d'indemnités pour {annee_str} introuvable."
    
    indemnities_data = {}
    try:
        df = pd.read_csv(chemin_fichier_indemnites, delimiter=';')
        # ... la logique de parsing du CSV reste la même
        for index, row in df.iterrows():
            code_dgfip = str(row["Code Pays"]).strip().upper()
            date_validite = datetime.strptime(str(row["Date Validité Barème"]).strip(), "%Y-%m-%d").date()
            montant_eur = float(str(row["Montant Barème (EUR)"]).strip())
            if code_dgfip not in indemnities_data: indemnities_data[code_dgfip] = []
            indemnities_data[code_dgfip].append({"date_validite": date_validite, "montant_eur": montant_eur})
        for code_p in indemnities_data:
            indemnities_data[code_p].sort(key=lambda x: x["date_validite"], reverse=True)
        return indemnities_data, f"Indemnités pour {annee_str} chargées."
    except Exception as e:
        return {}, f"Erreur chargement indemnités '{chemin_fichier_indemnites}': {e}"

def find_applicable_indemnity(code_dgfip_ou_iso, target_date_obj, indemnity_data_source):
    if not indemnity_data_source or code_dgfip_ou_iso not in indemnity_data_source: return 0.0 
    baremes_pour_code = indemnity_data_source[code_dgfip_ou_iso] 
    for bareme in baremes_pour_code:
        if bareme["date_validite"] <= target_date_obj: return bareme["montant_eur"]
    return 0.0

def convertir_ep5_heure_en_objet_temps(heure_ep5_str):
    try:
        if '.' in heure_ep5_str: h_str,c_str=heure_ep5_str.split('.',1);return(int(h_str),int(c_str.ljust(2,'0'))) 
        else: return (int(heure_ep5_str),0)
    except ValueError: return (0,0)

def calculer_date_segment(jour_str,ref_annee,ref_mois,date_depart_segment_pour_calcul_arrivee=None):
    try: jour=int(jour_str)
    except ValueError: raise 
    annee_calc=ref_annee; mois_calc=ref_mois
    if date_depart_segment_pour_calcul_arrivee: 
        annee_calc=date_depart_segment_pour_calcul_arrivee.year; mois_calc=date_depart_segment_pour_calcul_arrivee.month
        if jour < date_depart_segment_pour_calcul_arrivee.day: 
            mois_calc+=1
            if mois_calc > 12: mois_calc=1; annee_calc+=1
    try: return date(annee_calc,mois_calc,jour)
    except ValueError: raise

pattern_ep5_line = re.compile(
    r"^\s*\d+\s+"r"([A-Z0-9-]+)\s+"r"([A-Z0-9]+)\s+"r"([A-Z0-9]+)\s+"r"([A-Z]{3})\s+"
    r"(\d{1,2})\s*\|\s*(\d{1,2}\.\d{2,3})\s+"r"([A-Z]{3})\s+"r"(\d{1,2})\s*\|\s*(\d{1,2}\.\d{2,3})"
)

def analyser_page_ep5(texte_page_ep5,annee_base,mois_base,nom_fichier):
    segments_extraits=[]
    lignes=texte_page_ep5.split('\n')
    for ligne_idx,ligne in enumerate(lignes):
        match=pattern_ep5_line.search(ligne.strip()) 
        if match:
            try:
                # ... (même logique d'extraction de segment) ...
                avion_type_seg, avion_immat_seg = match.group(1), match.group(2)
                dep_airport_seg, dep_jour_seg_str = match.group(4), match.group(5).zfill(2)
                dep_heure_ep5_str, arr_airport_seg = match.group(6), match.group(7)
                arr_jour_seg_str, arr_heure_ep5_str = match.group(8).zfill(2), match.group(9)
                date_depart_seg=calculer_date_segment(dep_jour_seg_str,annee_base,mois_base)
                date_arrivee_seg=calculer_date_segment(arr_jour_seg_str,annee_base,mois_base,date_depart_segment_pour_calcul_arrivee=date_depart_seg)
                heure_depart_obj=convertir_ep5_heure_en_objet_temps(dep_heure_ep5_str)
                segments_extraits.append({'avion_type':avion_type_seg,'avion_immat':avion_immat_seg,
                    'dep_airport':dep_airport_seg,'dep_date':date_depart_seg,
                    'dep_heure_obj':heure_depart_obj,'arr_airport':arr_airport_seg,
                    'arr_date':date_arrivee_seg,'ligne_source_idx':ligne_idx,'nom_fichier':nom_fichier})
            except Exception: pass 
    if segments_extraits: segments_extraits.sort(key=lambda s:(s['dep_date'],s['dep_heure_obj']))
    
    # ... (même logique de reconstruction de rotation) ...
    rotations_trouvees=[]; en_rotation_active=False
    date_debut_rotation_actuelle=None; itineraire_en_cours=[] 
    segments_rotation_actuelle=[] 
    for segment in segments_extraits:
        if not en_rotation_active:
            if segment['dep_airport'] in BASES_FR:
                en_rotation_active=True; date_debut_rotation_actuelle=segment['dep_date']
                itineraire_en_cours=[segment['dep_airport'],segment['arr_airport']]
                segments_rotation_actuelle=[segment] 
        else: 
            itineraire_en_cours.append(segment['arr_airport']) 
            segments_rotation_actuelle.append(segment) 
            if segment['arr_airport'] in BASES_FR:
                date_fin_rotation_actuelle=segment['arr_date']
                duree_jours=(date_fin_rotation_actuelle - date_debut_rotation_actuelle).days + 1
                itineraire_simplifie = [itineraire_en_cours[0]] + [itineraire_en_cours[i] for i in range(1, len(itineraire_en_cours)) if itineraire_en_cours[i] != itineraire_en_cours[i-1]]
                rotations_trouvees.append({"Départ":date_debut_rotation_actuelle,"Retour":date_fin_rotation_actuelle,
                    "Durée":duree_jours,"Fichier":nom_fichier,"Itinéraire_aéroports":itineraire_simplifie,
                    "Segments_details":list(segments_rotation_actuelle)})
                en_rotation_active=False; date_debut_rotation_actuelle=None; itineraire_en_cours=[]; segments_rotation_actuelle=[]
    return rotations_trouvees,segments_extraits

def analyse_missions(uploaded_files):
    """
    Analyse les fichiers EP5, calcule les rotations et indemnités, et retourne toutes les données pour affichage.
    """
    toutes_les_rotations = []; tous_les_segments = [] 
    indemnity_data_par_annee = {}
    warnings = []

    for uploaded_file in uploaded_files:
        annee_fichier_base = 0; mois_fichier_base = 0
        # ... (votre logique complexe de détection de date reste la même) ...
        # ... on remplace juste st.warning par warnings.append(...) ...
        
        # Exemple de remplacement
        # if not (1<=mois_fichier_base<=12 and annee_fichier_base > 1990):
        #     warnings.append(f"Date PDF invalide pour '{uploaded_file.name}'. Ignoré.")
        #     continue
        nom_fichier_lower = uploaded_file.name.lower()
        match_date_pattern1 = re.search(r"(\d{2})(\d{4}|\d{2})", nom_fichier_lower)
        if match_date_pattern1:
            try:
                mois_candidat=int(match_date_pattern1.group(1))
                if 1<=mois_candidat<=12:
                    group2 = match_date_pattern1.group(2)
                    annee_fichier_base = int(f"20{group2}") if len(group2) == 2 else int(group2)
                    mois_fichier_base=mois_candidat
            except ValueError: pass
        
        # ... (la suite de la logique de détection de date) ...
            
        annee_actuelle_du_pdf = str(annee_fichier_base)
        if annee_actuelle_du_pdf not in indemnity_data_par_annee:
            indemnity_data, msg = load_indemnity_data(annee_actuelle_du_pdf)
            indemnity_data_par_annee[annee_actuelle_du_pdf] = indemnity_data
            warnings.append(msg)
            
        try:
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    texte = page.extract_text() or "" 
                    if "EP5" in texte.upper(): 
                        rotations_page, segments_page = analyser_page_ep5(texte, annee_fichier_base, mois_fichier_base, uploaded_file.name)
                        for r_p in rotations_page: r_p["Année_PDF"] = annee_actuelle_du_pdf
                        toutes_les_rotations.extend(rotations_page)
                        tous_les_segments.extend(segments_page) 
        except Exception as e:
            warnings.append(f"Erreur analyse PDF {uploaded_file.name}: {e}")
            continue

    if not toutes_les_rotations:
        return {"has_results": False, "warnings": warnings}

    # Dédoublonnage des rotations
    rotations_uniques_liste = []
    set_rotations_vues = set()
    for r_val in toutes_les_rotations:
        rotation_id_tuple = (r_val["Départ"], r_val["Retour"], tuple(r_val.get("Itinéraire_aéroports", [])))
        if rotation_id_tuple not in set_rotations_vues:
            rotations_uniques_liste.append(r_val)
            set_rotations_vues.add(rotation_id_tuple)
    rotations_uniques_liste.sort(key=lambda r_sort: r_sort["Départ"])

    # Calcul des indemnités et préparation du DataFrame
    annee_predominante = max(set(r.get("Année_PDF", "0") for r in rotations_uniques_liste))
    total_indemnites_annee_affichee = 0.0
    donnees_tableau = []

    for r_disp in rotations_uniques_liste:
        # ... (votre logique de calcul d'indemnité par rotation reste la même) ...
        itineraire_str = " → ".join(r_disp.get("Itinéraire_aéroports", ["N/A"]))
        # ...
        total_indemnites_rotation_individuelle = 0.0 # à calculer
        # ...
        donnees_tableau.append({
            "Mois Départ": r_disp["Départ"].strftime("%B %Y"), 
            "Itinéraire Global": itineraire_str,
            # ... autres colonnes
            "Indemnité Tot. (EUR)": total_indemnites_rotation_individuelle
        })
        total_indemnites_annee_affichee += total_indemnites_rotation_individuelle

    df_rotations = pd.DataFrame(donnees_tableau)

    # Préparation des stats avions
    df_types, df_immats = pd.DataFrame(), pd.DataFrame()
    if tous_les_segments: 
        types_avion = pd.Series(s['avion_type'] for s in tous_les_segments).value_counts().reset_index()
        types_avion.columns = ['Type Avion', 'Nombre de Segments']
        df_types = types_avion.sort_values(by='Nombre de Segments', ascending=False)
        
        immats_avion = pd.Series(s['avion_immat'] for s in tous_les_segments).value_counts().reset_index()
        immats_avion.columns = ['Immatriculation', 'Nombre de Segments']
        df_immats = immats_avion.sort_values(by='Nombre de Segments', ascending=False)

    return {
        "has_results": True,
        "rotations_df": df_rotations,
        "stats_avions_type_df": df_types,
        "stats_avions_immat_df": df_immats,
        "total_indemnites": total_indemnites_annee_affichee,
        "annee_predominante": annee_predominante,
        "warnings": warnings,
    }
