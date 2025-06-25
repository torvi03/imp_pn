import streamlit as st
import pdfplumber
import re
from datetime import datetime
import pandas as pd

def analyse_bulletins(uploaded_files):
    """
    Analyse les bulletins de paie PDF, extrait les données financières clés,
    et retourne un dictionnaire contenant un DataFrame et les totaux.
    NOTE : Cette fonction ne contient plus de code d'affichage Streamlit.
    """
    resultats_mensuels = {}
    mois_uniques = set()
    
    def extraire_date_nom(nom_fichier):
        try:
            base = nom_fichier.replace(".pdf", "")
            code_date_str = base[-6:] 
            if not code_date_str.isdigit() or len(code_date_str) != 6:
                match_alt = re.search(r"(\d{2})[_-]?(\d{4})", base)
                if match_alt:
                    code_date_str = match_alt.group(1) + match_alt.group(2)
                else:
                    match_alt_inv = re.search(r"(\d{4})(\d{2})", base)
                    if match_alt_inv:
                        code_date_str = match_alt_inv.group(2) + match_alt_inv.group(1)
                    else:
                        return None
            return datetime.strptime(code_date_str, "%m%Y")
        except Exception:
            return None

    fichiers_tries = sorted(uploaded_files, key=lambda f: extraire_date_nom(f.name) or datetime.min)
    cles_a_chercher = {
        "IR EXONEREES": "IR EXO",
        "IR NON EXONEREES": "IR NON EXO", 
        "REMB.CARTE NAVIGO": "IND TRANSPORT"
    }

    fichiers_ignores = []

    for fichier in fichiers_tries:
        date_obj = extraire_date_nom(fichier.name)
        if not date_obj:
            fichiers_ignores.append(fichier.name)
            continue

        mois_uniques.add((date_obj.year, date_obj.month))

        date_mois_str = date_obj.strftime("%B %Y")
        if date_mois_str not in resultats_mensuels:
            resultats_mensuels[date_mois_str] = {cle: [] for cle in cles_a_chercher.keys()}

        try:
            with pdfplumber.open(fichier) as pdf:
                if len(pdf.pages) > 0:
                    page_a_analyser = pdf.pages[0]
                    text_page = page_a_analyser.extract_text()
                    
                    if text_page:
                        for line in text_page.split('\n'):
                            for cle_longue in cles_a_chercher.keys():
                                if cle_longue in line:
                                    match_montants = re.findall(r"-?\s*\d+[\.,]\d{2}", line)
                                    if match_montants:
                                        valeur_str = match_montants[-1].replace(" ", "").replace(",", ".")
                                        try:
                                            montant = float(valeur_str)
                                            resultats_mensuels[date_mois_str][cle_longue].append(montant)
                                        except ValueError:
                                            pass
        except Exception as e:
            fichiers_ignores.append(f"{fichier.name} (erreur de lecture: {e})")


    if not resultats_mensuels:
        return {
            "dataframe": pd.DataFrame(),
            "totaux_par_cle": {},
            "total_general": 0.0,
            "fichiers_ignores": fichiers_ignores
        }

    # --- PRÉPARATION DES DONNÉES POUR LE DATAFRAME ---
    donnees_tableau = []
    cles_mois_tries = sorted(resultats_mensuels.keys(), key=lambda mois_str_key: datetime.strptime(mois_str_key, "%B %Y"))

    for mois_str_key in cles_mois_tries:
        data_mois = resultats_mensuels[mois_str_key]
        ligne_tableau = {"MOIS": mois_str_key.capitalize()}
        total_ligne = 0.0 # Initialiser le total pour cette ligne

        for cle_longue, cle_courte in cles_a_chercher.items():
            montant = sum(data_mois.get(cle_longue, []))
            ligne_tableau[cle_courte] = montant
            total_ligne += montant # Ajouter le montant au total de la ligne
        
        # --- AJOUT DE LA COLONNE TOTAL ---
        ligne_tableau["TOTAL"] = total_ligne
        # --- FIN DE L'AJOUT ---

        donnees_tableau.append(ligne_tableau)
    
    # --- CRÉATION DU DATAFRAME ---
    df = pd.DataFrame()
    if donnees_tableau:
        df = pd.DataFrame(donnees_tableau)
        
        # S'assurer que la colonne TOTAL est la dernière
        colonnes = list(df.columns)
        if "TOTAL" in colonnes:
            colonnes.remove("TOTAL")
            colonnes.append("TOTAL")
            df = df[colonnes]
        
        # Calcul des totaux
        # On exclut la nouvelle colonne TOTAL du calcul du total général pour ne pas le compter deux fois
        totaux_par_cle = {col: df[col].sum() for col in df.columns if col not in ['MOIS', 'TOTAL']}
        total_general = sum(totaux_par_cle.values())
        
        return {
            "dataframe": df,
            "totaux_par_cle": totaux_par_cle,
            "total_general": total_general,
            "fichiers_ignores": fichiers_ignores
            "mois_comptes": len(mois_uniques)
        }
    else:
        return {
            "dataframe": pd.DataFrame(),
            "totaux_par_cle": {cle_courte: 0.0 for cle_courte in cles_a_chercher.values()},
            "total_general": 0.0,
            "fichiers_ignores": fichiers_ignores
            "mois_comptes": len(mois_uniques) 
        }
