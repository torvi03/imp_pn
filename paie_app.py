import streamlit as st
import pdfplumber
import re
from datetime import datetime

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
    cles_a_chercher = ["IR EXONEREES", "IR NON EXONEREES", "REMB.CARTE NAVIGO"]

    for fichier in fichiers_tries:
        date_obj = extraire_date_nom(fichier.name)
        if date_obj == datetime.min and fichier.name != "":
            st.error(f"Fichier '{fichier.name}' ignoré (date non déterminée).")
            continue

        date_mois_str = date_obj.strftime("%B %Y")
        if date_mois_str not in resultats_mensuels:
            resultats_mensuels[date_mois_str] = {cle: [] for cle in cles_a_chercher}

        try:
            with pdfplumber.open(fichier) as pdf:
                # --- OPTIMISATION 1 : Ne lire que la première page ---
                if len(pdf.pages) > 0:
                    page_a_analyser = pdf.pages[0]
                    text_page = page_a_analyser.extract_text()
                    
                    if text_page:
                        # --- APPROCHE FIABLE : Parcourir les lignes de cette page ---
                        for line in text_page.split('\n'):
                            for cle in cles_a_chercher:
                                if cle in line: # Si le mot-clé est sur la ligne
                                    # Regex pour trouver le DERNIER montant sur la ligne
                                    match_montants = re.findall(r"-?\s*\d+[\.,]\d{2}", line)
                                    if match_montants:
                                        valeur_str = match_montants[-1].replace(" ", "").replace(",", ".")
                                        try:
                                            montant = float(valeur_str)
                                            resultats_mensuels[date_mois_str][cle].append(montant)
                                        except ValueError:
                                            pass # Ignorer si la conversion en nombre échoue
                    # else:
                        # st.info(f"La première page de {fichier.name} ne contient pas de texte.")
                # else:
                    # st.warning(f"Le fichier {fichier.name} est vide (0 page).")

        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier PDF {fichier.name} : {e}")
            if date_mois_str not in resultats_mensuels :
                 resultats_mensuels[date_mois_str] = {cle_init: [] for cle_init in cles_a_chercher}

    if not resultats_mensuels:
        st.info("Aucune donnée n'a pu être extraite des bulletins de paie fournis.")
        return

    st.header("📊 Résultats mensuels")
    totaux = {cle: 0.0 for cle in cles_a_chercher}
    
    cles_mois_tries = sorted(resultats_mensuels.keys(), key=lambda mois_str_key: datetime.strptime(mois_str_key, "%B %Y"))

    for mois_str_key in cles_mois_tries:
        data = resultats_mensuels[mois_str_key]
        st.subheader(mois_str_key)
        mois_a_des_donnees = False
        for cle, valeurs in data.items():
            if valeurs:
                total_cle_mois = sum(valeurs)
                st.write(f"**{cle}** : {valeurs} → Total : {total_cle_mois:.2f} €")
                totaux[cle] += total_cle_mois
                mois_a_des_donnees = True
        if not mois_a_des_donnees:
            st.write("Aucune des valeurs cibles n'a été trouvée pour ce mois.")
        st.markdown("---")

    st.header("🧾 Totaux annuels")
    au_moins_un_total_annuel = False
    for cle, total_annuel_cle in totaux.items():
        if total_annuel_cle != 0.0 :
             st.write(f"**{cle}** : {total_annuel_cle:.2f} €")
             au_moins_un_total_annuel = True
    
    if au_moins_un_total_annuel:
        st.markdown("### **Total général des sommes extraites : {:.2f} €**".format(sum(totaux.values())))
        
        return {
        "totaux_par_cle": totaux,
        "total_general": sum(totaux.values())
              }
    else:
        st.info("Aucun montant significatif n'a été extrait pour calculer les totaux annuels.")
