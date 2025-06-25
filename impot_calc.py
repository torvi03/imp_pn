import streamlit as st
from paie_app import analyse_bulletins
from ep5_app import analyse_missions
from attestation_app import analyse_attestation_nuitees

# Configuration de la page
st.set_page_config(
    page_title="Impôt Calc ✨",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Initialisation de l'état de la session ---
# On utilise des clés distinctes pour chaque type de résultat
if 'resultats_paie' not in st.session_state:
    st.session_state.resultats_paie = None
if 'resultats_ep5' not in st.session_state:
    st.session_state.resultats_ep5 = None
if 'resultats_attestation' not in st.session_state:
    st.session_state.resultats_attestation = None
if 'menu_actif' not in st.session_state:
    st.session_state.menu_actif = None

# --- Fonctions pour changer le menu actif ---
def activer_menu(menu):
    st.session_state.menu_actif = menu

# --- PAGE PRINCIPALE ---
st.title("📊 Comptabilité de Vol")
st.markdown("---")

# Créer deux colonnes principales
col_gauche, col_droite = st.columns([1, 2])

# --- COLONNE DE GAUCHE (Contrôles) ---
with col_gauche:
    st.header("🗂️ Analyses Disponibles")
    st.write("Cliquez sur une analyse pour téléverser les fichiers correspondants.")
    
    st.button("💵 Analyse des Bulletins de Paie", on_click=activer_menu, args=('paie',), use_container_width=True)
    st.button("✈️ Analyse des Rotations (EP5)", on_click=activer_menu, args=('ep5',), use_container_width=True)
    st.button("🏠 Analyse Attestation Nuitées", on_click=activer_menu, args=('attestation',), use_container_width=True)

    st.markdown("---")

    # Afficher l'uploader de fichiers en fonction du menu actif
    fichiers_analyses = None
    if st.session_state.menu_actif == 'paie':
        with st.container(border=True):
            st.subheader("Téléverser Bulletins de Paie")
            fichiers_analyses = st.file_uploader(
                "Sélectionnez vos fichiers PDF de paie :", type="pdf",
                accept_multiple_files=True, key="paie_uploader"
            )
            
    elif st.session_state.menu_actif == 'ep5':
        with st.container(border=True):
            st.subheader("Téléverser Fichiers EP5")
            fichiers_analyses = st.file_uploader(
                "Sélectionnez vos fichiers PDF EP4/EP5 :", type="pdf",
                accept_multiple_files=True, key="ep5_uploader"
            )

    elif st.session_state.menu_actif == 'attestation':
        with st.container(border=True):
            st.subheader("Téléverser Attestations")
            fichiers_analyses = st.file_uploader(
                "Sélectionnez les PDF contenant les attestations annuelles :", type="pdf",
                accept_multiple_files=True, key="attestation_uploader"
            )

# --- COLONNE DE DROITE (Résultats) ---
with col_droite:
    st.header("📈 Résultats de l'Analyse")

    # Lancer l'analyse si des fichiers ont été téléversés
    # On met les résultats dans la session state pour qu'ils persistent
    if fichiers_analyses:
        with st.spinner(f"Analyse de {len(fichiers_analyses)} fichier(s) en cours... ⏳"):
            if st.session_state.menu_actif == 'paie':
                st.session_state.resultats_paie = analyse_bulletins(fichiers_analyses)
                st.session_state.resultats_ep5 = None # On réinitialise les autres résultats
                st.session_state.resultats_attestation = None
            elif st.session_state.menu_actif == 'ep5':
                # analyse_missions affiche encore ses propres résultats, on le modifiera plus tard
                analyse_missions(fichiers_analyses) 
                st.session_state.resultats_paie = None
                st.session_state.resultats_attestation = None
                st.balloons()
            elif st.session_state.menu_actif == 'attestation':
                # analyse_attestation_nuitees affiche aussi ses propres résultats
                analyse_attestation_nuitees(fichiers_analyses)
                st.session_state.resultats_paie = None
                st.session_state.resultats_ep5 = None
    
    # --- NOUVEAU : Bloc d'affichage centralisé pour les résultats de paie ---
    if st.session_state.resultats_paie:
        with st.container(border=True):
            resultats = st.session_state.resultats_paie
            df = resultats.get("dataframe")

            st.subheader("💵 Synthèse des Bulletins de Paie")

            if resultats.get("fichiers_ignores"):
                with st.expander("Avertissements sur certains fichiers"):
                    for nom_fichier in resultats["fichiers_ignores"]:
                        st.warning(f"Le fichier '{nom_fichier}' n'a pas pu être traité (date non reconnue ou erreur).")

            if not df.empty:
                # Affichage du tableau mensuel
                st.markdown("##### Synthèse Mensuelle")
                st.dataframe(df, hide_index=True, use_container_width=True)
                
                # Affichage des totaux annuels
                st.markdown("##### Totaux Annuels")
                totaux_par_cle = resultats.get("totaux_par_cle", {})
                total_general = resultats.get("total_general", 0.0)

                # Utiliser des colonnes pour un affichage propre des métriques
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("IR Exonérées", f"{totaux_par_cle.get('IR EXO', 0.0):.2f} €")
                with col2:
                    st.metric("IR Non Exonérées", f"{totaux_par_cle.get('IR NON EXO', 0.0):.2f} €")
                with col3:
                    st.metric("Indemnité Transport", f"{totaux_par_cle.get('IND TRANSPORT', 0.0):.2f} €")

                st.markdown(f"#### Total Général des Sommes Extraites : **{total_general:.2f} €**")
            else:
                st.info("Aucune donnée n'a pu être extraite des bulletins de paie fournis.")

    # Espace réservé pour les futurs affichages centralisés (EP5, Attestation)
    # if st.session_state.resultats_ep5:
    #     # Le code d'affichage pour EP5 viendra ici
    #     pass

    # Message d'accueil si rien n'est encore affiché
    if not st.session_state.resultats_paie and not st.session_state.resultats_ep5 and not st.session_state.resultats_attestation:
        if st.session_state.menu_actif:
            st.info("Les résultats s'afficheront ici après l'analyse des fichiers téléversés.")
        else:
            st.info("Veuillez choisir une analyse et téléverser des fichiers.")

