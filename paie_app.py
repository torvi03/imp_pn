import streamlit as st
import pdfplumber
import re
from datetime import datetime
import pandas as pd # S'assurer que pandas est importé

def analyse_bulletins(uploaded_files):
    resultats_mensuels = {}
    
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
                        st.warning(f"Format de date non reconnu dans : {nom_fichier}.")
                        return datetime.min 
            return datetime.strptime(code_date_str, "%m%Y")
        except Exception:
            st.warning(f"Erreur de parsing de date pour : {nom_fichier}.")
            return datetime.min

    fichiers_tries = sorted(uploaded_files, key=lambda f: extraire_date_nom(f.name))
    cles_a_chercher = {
        "IR EXONEREES": "IR EXO",
        "IR NON EXONEREES": "IR NON EXO", 
        "REMB.CARTE NAVIGO": "IND TRANSPORT"
    }

    for fichier in fichiers_tries:
        date_obj = extraire_date_nom(fichier.name)
        if date_obj == datetime.min and fichier.name != "":
            st.error(f"Fichier '{fichier.name}' ignoré (date non déterminée).")
            continue

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
            st.error(f"Erreur lors de la lecture du fichier PDF {fichier.name} : {e}")
            if date_mois_str not in resultats_mensuels :
                 resultats_mensuels[date_mois_str] = {cle_init: [] for cle_init in cles_a_chercher.keys()}

    if not resultats_mensuels:
        st.info("Aucune donnée n'a pu être extraite des bulletins de paie fournis.")
        return

    st.header("📊 Synthèse Annuelle de la Paie")
    
    # --- PRÉPARATION DES DONNÉES POUR LE TABLEAU ---
    donnees_tableau = []
    cles_mois_tries = sorted(resultats_mensuels.keys(), key=lambda mois_str_key: datetime.strptime(mois_str_key, "%B %Y"))

    for mois_str_key in cles_mois_tries:
        data_mois = resultats_mensuels[mois_str_key]
        ligne_tableau = {"MOIS": mois_str_key.capitalize()} # Mettre la première lettre en majuscule
        for cle_longue, cle_courte in cles_a_chercher.items():
            ligne_tableau[cle_courte] = sum(data_mois[cle_longue])
        donnees_tableau.append(ligne_tableau)
    
    # --- CRÉATION ET AFFICHAGE DU DATAFRAME ---
    if donnees_tableau:
        df = pd.DataFrame(donnees_tableau)

        # Création de la ligne de totaux
        total_row = df.sum(numeric_only=True).to_frame().T
        total_row['MOIS'] = 'TOTAL ANNUEL'
        
        # Style du DataFrame pour affichage
        st.dataframe(df, hide_index=True, use_container_width=True)
        
        # Affichage des totaux de manière distincte en dessous
        st.markdown("---")
        st.subheader("🧾 Totaux Annuels")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("IR Exonérées", f"{total_row['IR EXO'].iloc[0]:.2f} €")
        with col2:
            st.metric("IR Non Exonérées", f"{total_row['IR NON EXO'].iloc[0]:.2f} €")
        with col3:
            st.metric("Indemnité Transport", f"{total_row['IND TRANSPORT'].iloc[0]:.2f} €")

        total_general = total_row.drop(columns='MOIS').sum(axis=1).iloc[0]
        st.markdown(f"#### Total Général des Sommes Extraites : **{total_general:.2f} €**")
        
        # Retourner les résultats pour une utilisation potentielle dans le script principal
        return {
            "dataframe": df,
            "totals": total_row.to_dict('records')[0]
        }
    else:
        st.info("Aucun montant significatif n'a été extrait pour construire le tableau.")
