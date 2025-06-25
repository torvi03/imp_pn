import streamlit as st
from paie_app import analyse_bulletins
from ep5_app import analyse_missions
from attestation_app import analyse_attestation_nuitees
import pandas as pd

# --- Configuration de la page ---
st.set_page_config(
    page_title="Impôt Calc ✨",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Fonctions utilitaires ---
@st.cache_data
def convert_df_to_csv(df):
    """Convertit un DataFrame en CSV (UTF-8) pour le téléchargement."""
    # Important : l'encodage 'utf-8-sig' est souvent meilleur pour l'ouverture dans Excel
    return df.to_csv(index=False, sep=';').encode('utf-8-sig')

# --- Initialisation de l'état de la session ---
if 'resultats_paie' not in st.session_state:
    st.session_state.resultats_paie = None
if 'resultats_ep5' not in st.session_state:
    st.session_state.resultats_ep5 = None
if 'resultats_attestation' not in st.session_state:
    st.session_state.resultats_attestation = None
if 'menu_actif' not in st.session_state:
    st.session_state.menu_actif = None

# --- Fonctions de navigation ---
def activer_menu(menu):
    """Change le menu actif et réinitialise les résultats pour un nouveau calcul."""
    st.session_state.menu_actif = menu
    st.session_state.resultats_paie = None
    st.session_state.resultats_ep5 = None
    st.session_state.resultats_attestation = None

# --- INTERFACE PRINCIPALE ---
st.title("📊 Comptabilité de Vol")
st.markdown("---")

col_gauche, col_droite = st.columns([1, 2])

# --- COLONNE DE GAUCHE (Contrôles & Uploads) ---
with col_gauche:
    st.header("🗂️ Analyses Disponibles")
    st.write("Choisissez une analyse pour commencer.")
    
    st.button("💵 Analyse des Bulletins de Paie", on_click=activer_menu, args=('paie',), use_container_width=True)
    st.button("✈️ Analyse des Rotations (EP5)", on_click=activer_menu, args=('ep5',), use_container_width=True)
    st.button("🏠 Analyse Attestation Nuitées", on_click=activer_menu, args=('attestation',), use_container_width=True)

    st.markdown("---")

    fichiers_analyses = None
    if st.session_state.menu_actif == 'paie':
        with st.container(border=True):
            st.subheader("Téléverser Bulletins de Paie")
            fichiers_analyses = st.file_uploader("Sélectionnez vos fichiers PDF de paie :", type="pdf", accept_multiple_files=True, key="paie_uploader")
    elif st.session_state.menu_actif == 'ep5':
        with st.container(border=True):
            st.subheader("Téléverser Fichiers EP5")
            fichiers_analyses = st.file_uploader("Sélectionnez vos fichiers PDF EP4/EP5 :", type="pdf", accept_multiple_files=True, key="ep5_uploader")
    elif st.session_state.menu_actif == 'attestation':
        with st.container(border=True):
            st.subheader("Téléverser Attestations")
            fichiers_analyses = st.file_uploader("Sélectionnez les PDF contenant les attestations annuelles :", type="pdf", accept_multiple_files=True, key="attestation_uploader")

# --- COLONNE DE DROITE (Affichage des Résultats) ---
with col_droite:
    st.header("📈 Résultats de l'Analyse")

    if fichiers_analyses:
        with st.spinner(f"Analyse de {len(fichiers_analyses)} fichier(s) en cours... ⏳"):
            if st.session_state.menu_actif == 'paie':
                st.session_state.resultats_paie = analyse_bulletins(fichiers_analyses)
            elif st.session_state.menu_actif == 'ep5':
                st.session_state.resultats_ep5 = analyse_missions(fichiers_analyses)
            elif st.session_state.menu_actif == 'attestation':
                st.session_state.resultats_attestation = analyse_attestation_nuitees(fichiers_analyses)

    # --- Bloc d'affichage pour les résultats de PAIE ---
    if st.session_state.resultats_paie:
        with st.container(border=True):
            res = st.session_state.resultats_paie
            st.subheader("💵 Synthèse des Bulletins de Paie")

            df = res.get("dataframe")
            if isinstance(df, pd.DataFrame) and not df.empty:
                st.markdown("##### Synthèse Mensuelle")
                st.dataframe(df, hide_index=True, use_container_width=True)

                # --- AJOUT DU BOUTON DE TÉLÉCHARGEMENT ---
                csv_paie = convert_df_to_csv(df)
                st.download_button(
                    label="📥 Télécharger la synthèse de paie (CSV)",
                    data=csv_paie,
                    file_name=f"synthese_paie.csv",
                    mime='text/csv',
                )
                st.markdown("---")
                # --- FIN DE L'AJOUT ---
                
                st.markdown("##### Totaux Annuels")
                # ... (le reste de l'affichage des totaux reste identique) ...
            else:
                st.info("Aucune donnée n'a pu être extraite des bulletins de paie valides.")

    # --- Bloc d'affichage pour les résultats EP5 ---
    if st.session_state.resultats_ep5:
        with st.container(border=True):
            res = st.session_state.resultats_ep5
            st.subheader("✈️ Synthèse des Rotations (EP5)")

            if res.get("has_results"):
                st.metric(label=f"💰 Total Indemnités Estimées pour {res.get('annee_predominante', 'N/A')}", value=f"{res.get('total_indemnites', 0.0):.2f} EUR")
                st.markdown("---")
                
                tab_rot, tab_stats = st.tabs(["📅 Tableau des Rotations", "✈️ Statistiques Avions"])
                with tab_rot:
                    df_rotations = res.get("rotations_df", pd.DataFrame())
                    st.dataframe(df_rotations, hide_index=True, use_container_width=True)
                    
                    # --- AJOUT DU BOUTON DE TÉLÉCHARGEMENT ---
                    if not df_rotations.empty:
                        csv_rotations = convert_df_to_csv(df_rotations)
                        st.download_button(
                           label="📥 Télécharger le tableau des rotations (CSV)",
                           data=csv_rotations,
                           file_name=f"synthese_rotations_{res.get('annee_predominante', 'data')}.csv",
                           mime='text/csv',
                        )
                    # --- FIN DE L'AJOUT ---

                with tab_stats:
                    # ... (le reste de l'affichage des statistiques reste identique) ...
            else:
                st.warning("Aucune rotation ou segment de vol n'a pu être extrait des fichiers fournis.")

    # --- Bloc d'affichage pour les résultats d'ATTESTATION ---
    if st.session_state.resultats_attestation:
        # ... (ce bloc reste identique car il n'y a pas de tableau à exporter) ...

    # --- Message d'accueil si aucune analyse n'est lancée ---
    # ... (ce bloc reste identique) ...
