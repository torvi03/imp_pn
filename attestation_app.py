import streamlit as st
import pdfplumber
import re

def analyse_attestation_nuitees(uploaded_files):
    """
    Analyse les fichiers PDF téléversés pour trouver la page d'attestation des nuitées
    et extraire le montant total des frais d'hébergement.
    """
    resultats_annuels = {} # Dictionnaire pour stocker les résultats : { "année": montant }

    st.header("🏠 Analyse des Attestations de Nuitées")

    for fichier in uploaded_files:
        try:
            with pdfplumber.open(fichier) as pdf:
                page_trouvee = False
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if not text:
                        continue

                    # 1. Identifier la page en cherchant le titre spécifique (insensible à la casse)
                    match_titre = re.search(r"ATTESTATION DE DECOMPTE DES NUITEES POUR L'ANNEE\s+(\d{4})", text, re.IGNORECASE)
                    
                    if match_titre:
                        annee_attestation = match_titre.group(1)
                        page_trouvee = True
                        
                        # 2. Une fois la page trouvée, chercher la phrase avec le montant
                        # Regex pour trouver un nombre (entier ou décimal avec . ou ,) après "s'élève à"
                        match_montant = re.search(r"s'élève à\s+([\d\s.,]+)\s+Euros", text, re.IGNORECASE)
                        
                        if match_montant:
                            valeur_extraite_str = match_montant.group(1)
                            # Nettoyer la chaîne : enlever les espaces, remplacer la virgule par un point
                            valeur_nettoyee_str = valeur_extraite_str.replace(" ", "").replace(",", ".")
                            try:
                                montant_total = float(valeur_nettoyee_str)
                                resultats_annuels[annee_attestation] = montant_total
                                st.write(f"✓ Fichier **{fichier.name}** : Attestation pour l'année **{annee_attestation}** trouvée. Montant des frais : **{montant_total:.2f} €**")
                            except ValueError:
                                st.warning(f"Dans {fichier.name}, une valeur a été trouvée pour l'année {annee_attestation} mais n'a pas pu être convertie en nombre : '{valeur_extraite_str}'")
                        else:
                            st.warning(f"Dans {fichier.name}, la page d'attestation pour l'année {annee_attestation} a été trouvée, mais la ligne avec le montant total est manquante ou dans un format inattendu.")
                        
                        break # On a trouvé la page, on passe au fichier suivant
                
                if not page_trouvee:
                    st.info(f"Le fichier '{fichier.name}' a été analysé, mais aucune 'Attestation de décompte des nuitées' n'a été trouvée.")

        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier PDF {fichier.name} : {e}")

    # Affichage du résumé final
    if resultats_annuels:
        st.markdown("---")
        st.subheader("Synthèse des Frais d'Hébergement")
        
        # Trier les résultats par année pour un affichage chronologique
        annees_triees = sorted(resultats_annuels.keys(), reverse=True)
        
        for annee in annees_triees:
            montant = resultats_annuels[annee]
            st.metric(label=f"Total Frais Hébergement pour l'année {annee}", value=f"{montant:.2f} €")
    else:
        st.info("Aucune information sur les frais d'hébergement n'a pu être extraite des fichiers fournis.")
