import streamlit as st
import pdfplumber
import re

def analyse_attestation_nuitees(uploaded_files):
    """
    Analyse les PDF d'attestation de nuitées et retourne les montants extraits.
    NOTE : Ne contient plus de code d'affichage Streamlit.
    """
    resultats_annuels = {}  # { "année": montant }
    fichiers_sans_attestation = []
    erreurs = []

    for fichier in uploaded_files:
        try:
            with pdfplumber.open(fichier) as pdf:
                page_trouvee = False
                for page in pdf.pages:
                    text = page.extract_text()
                    if not text:
                        continue

                    # 1. Identifier la page par son titre
                    match_titre = re.search(r"ATTESTATION DE DECOMPTE DES NUITEES POUR L'ANNEE\s+(\d{4})", text, re.IGNORECASE)
                    
                    if match_titre:
                        annee_attestation = match_titre.group(1)
                        page_trouvee = True
                        
                        # 2. Chercher la phrase avec le montant
                        match_montant = re.search(r"s'élève à\s+([\d\s.,]+)\s+Euros", text, re.IGNORECASE)
                        
                        if match_montant:
                            valeur_extraite_str = match_montant.group(1)
                            valeur_nettoyee_str = valeur_extraite_str.replace(" ", "").replace(",", ".")
                            try:
                                montant_total = float(valeur_nettoyee_str)
                                resultats_annuels[annee_attestation] = montant_total
                            except ValueError:
                                erreurs.append(f"Fichier {fichier.name} ({annee_attestation}): valeur '{valeur_extraite_str}' non convertible.")
                        else:
                            erreurs.append(f"Fichier {fichier.name} ({annee_attestation}): page trouvée mais montant manquant.")
                        
                        break  # Page trouvée, passer au fichier suivant
                
                if not page_trouvee:
                    fichiers_sans_attestation.append(fichier.name)

        except Exception as e:
            erreurs.append(f"Erreur de lecture du fichier {fichier.name} : {e}")

    return {
        "resultats": resultats_annuels,
        "erreurs": erreurs,
        "fichiers_sans_attestation": fichiers_sans_attestation
    }
