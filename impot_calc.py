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
    """Convertit un DataFrame en CSV (UTF-8 avec BOM) pour le téléchargement."""
    return df.to_csv(index=False, sep=';').encode('utf-8-sig')

# --- Initialisation de l'état de la session ---
if 'menu_actif' not in st.session_state:
    st.session_state.menu_actif = None
if 'resultats_paie' not in st.session_state:
    st.session_state.resultats_paie = None
if 'resultats_ep5' not in st.session_state:
    st.session_state.resultats_ep5 = None
if 'resultats_attestation' not in st.session_state:
    st.session_state.resultats_attestation = None
if 'show_synthese' not in st.session_state:
    st.session_state.show_synthese = False

# --- Fonctions de navigation ---
def activer_menu(menu):
    """Change le menu d'analyse actif et cache la synthèse."""
    st.session_state.menu_actif = menu
    st.session_state.show_synthese = False

def activer_synthese():
    """Active l'affichage de la synthèse et cache les analyses individuelles."""
    st.session_state.show_synthese = True
    st.session_state.menu_actif = None


# --- INTERFACE PRINCIPALE ---
st.title("📊 Comptabilité de Vol")
st.markdown("---")

col_gauche, col_droite = st.columns([1, 2])

# --- COLONNE DE GAUCHE (Contrôles & Uploads) ---
with col_gauche:
    st.header("🗂️ Actions")
    
    st.button("SYNTHESE ANNUELLE", on_click=activer_synthese, use_container_width=True, type="primary")
    
    with st.expander("Analyses individuelles"):
        st.button("💵 Analyse des Bulletins de Paie", on_click=activer_menu, args=('paie',), use_container_width=True)
        st.button("✈️ Analyse des Rotations (EP5)", on_click=activer_menu, args=('ep5',), use_container_width=True)
        st.button("🏠 Analyse Attestation Nuitées", on_click=activer_menu, args=('attestation',), use_container_width=True)

    st.markdown("---")
    
    fichiers_analyses = None
    if st.session_state.menu_actif == 'paie':
        with st.container(border=True):
            st.subheader("Téléverser Bulletins de Paie")
            fichiers_analyses = st.file_uploader("Sélectionnez vos PDF de paie :", type="pdf", accept_multiple_files=True, key="paie_uploader")
    elif st.session_state.menu_actif == 'ep5':
        with st.container(border=True):
            st.subheader("Téléverser Fichiers EP5")
            fichiers_analyses = st.file_uploader("Sélectionnez vos PDF EP5 :", type="pdf", accept_multiple_files=True, key="ep5_uploader")
    elif st.session_state.menu_actif == 'attestation':
        with st.container(border=True):
            st.subheader("Téléverser Attestations")
            fichiers_analyses = st.file_uploader("Sélectionnez vos PDF d'attestations :", type="pdf", accept_multiple_files=True, key="attestation_uploader")

# --- COLONNE DE DROITE (Affichage des Résultats) ---
with col_droite:
    st.header("📈 Résultats")

    if fichiers_analyses:
        with st.spinner(f"Analyse de {len(fichiers_analyses)} fichier(s)... ⏳"):
            if st.session_state.menu_actif == 'paie':
                st.session_state.resultats_paie = analyse_bulletins(fichiers_analyses)
            elif st.session_state.menu_actif == 'ep5':
                st.session_state.resultats_ep5 = analyse_missions(fichiers_analyses)
            elif st.session_state.menu_actif == 'attestation':
                st.session_state.resultats_attestation = analyse_attestation_nuitees(fichiers_analyses)

    # --- Bloc d'affichage pour la SYNTHESE ANNUELLE ---
    if st.session_state.show_synthese:
        with st.container(border=True):
            st.subheader(f"🧮 Synthèse Annuelle Globale")
            
            res_paie = st.session_state.resultats_paie
            res_ep5 = st.session_state.resultats_ep5
            res_attest = st.session_state.resultats_attestation
            
            total_paie = res_paie.get("total_general", 0.0) if res_paie else 0.0
            total_ep5 = res_ep5.get("total_indemnites", 0.0) if res_ep5 else 0.0
            total_attestation = sum(res_attest["resultats"].values()) if res_attest and res_attest.get("resultats") else 0.0
            grand_total = total_paie + total_ep5 + total_attestation
            
            st.markdown("Voici le résumé des montants calculés à partir de vos dernières analyses.")
            
            if not any([res_paie, res_ep5, res_attest]):
                 st.warning("Aucune analyse n'a encore été effectuée. Veuillez lancer une analyse individuelle avant de demander la synthèse.")
            else:
                st.metric("💵 Total des indemnités de Paie", f"{total_paie:.2f} €", help="Calculé depuis la dernière analyse de paie.")
                st.metric("✈️ Total des indemnités de découcher (EP5)", f"{total_ep5:.2f} €", help="Calculé depuis la dernière analyse EP5.")
                st.metric("🏠 Total des frais d'hébergement (Attestations)", f"{total_attestation:.2f} €", help="Calculé depuis la dernière analyse d'attestations.")
                st.markdown("---")
                st.markdown(f"### 💰 Total Général à considérer : **{grand_total:.2f} €**")
    
    # --- Affichage des résultats des analyses individuelles ---
    elif st.session_state.menu_actif == 'paie' and st.session_state.resultats_paie:
        with st.container(border=True):
            res = st.session_state.resultats_paie
            st.subheader("💵 Synthèse des Bulletins de Paie")

            df = res.get("dataframe")
            if isinstance(df, pd.DataFrame) and not df.empty:
                st.markdown("##### Synthèse Mensuelle")
                st.dataframe(df, hide_index=True, use_container_width=True)

                csv_paie = convert_df_to_csv(df)
                st.download_button("📥 Télécharger la synthèse de paie (CSV)", csv_paie, "synthese_paie.csv", 'text/csv')
                st.markdown("---")
                
                st.markdown("##### Totaux Annuels")
                totaux = res.get("totaux_par_cle", {})
                c1, c2, c3 = st.columns(3)
                c1.metric("IR Exonérées", f"{totaux.get('IR EXO', 0.0):.2f} €")
                c2.metric("IR Non Exonérées", f"{totaux.get('IR NON EXO', 0.0):.2f} €")
                c3.metric("Indemnité Transport", f"{totaux.get('IND TRANSPORT', 0.0):.2f} €")
                st.markdown(f"#### Total Général : **{res.get('total_general', 0.0):.2f} €**")
            else:
                st.info("Aucune donnée n'a pu être extraite des bulletins de paie valides.")

    elif st.session_state.menu_actif == 'ep5' and st.session_state.resultats_ep5:
        with st.container(border=True):
            res = st.session_state.resultats_ep5
            st.subheader("✈️ Synthèse des Rotations (EP5)")

            if res.get("has_results"):
                st.metric(f"💰 Total Indemnités Estimées pour {res.get('annee_predominante', 'N/A')}", f"{res.get('total_indemnites', 0.0):.2f} EUR")
                st.markdown("---")
                
                tab_rot, tab_stats = st.tabs(["📅 Tableau des Rotations", "✈️ Statistiques Avions"])
                with tab_rot:
                    df_rotations = res.get("rotations_df", pd.DataFrame())
                    st.dataframe(df_rotations, hide_index=True, use_container_width=True)
                    if not df_rotations.empty:
                        csv_rotations = convert_df_to_csv(df_rotations)
                        st.download_button("📥 Télécharger les rotations (CSV)", csv_rotations, f"synthese_rotations_{res.get('annee_predominante', 'data')}.csv", 'text/csv')
                with tab_stats:
                    st.markdown("Statistiques par segment de vol :")
                    df_types = res.get("stats_avions_type_df")
                    df_immats = res.get("stats_avions_immat_df")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Par Type d'Avion :**")
                        if isinstance(df_types, pd.DataFrame) and not df_types.empty:
                            st.bar_chart(df_types.set_index('Type Avion'))
                    with col2:
                        st.write("**Par Immatriculation :**")
                        if isinstance(df_immats, pd.DataFrame) and not df_immats.empty:
                            st.bar_chart(df_immats.set_index('Immatriculation'))
            else:
                st.warning("Aucune rotation ou segment de vol n'a pu être extrait.")

    elif st.session_state.menu_actif == 'attestation' and st.session_state.resultats_attestation:
        with st.container(border=True):
            res = st.session_state.resultats_attestation
            st.subheader("🏠 Synthèse des Attestations de Nuitées")
            resultats_annuels = res.get("resultats", {})
            if resultats_annuels:
                resultats_tries = sorted(resultats_annuels.items(), key=lambda item: item[0], reverse=True)
                for annee, montant in resultats_tries:
                    st.metric(f"Total Frais Hébergement pour {annee}", f"{montant:.2f} €")
            else:
                st.info("Aucune information sur les frais d'hébergement n'a pu être extraite.")
    
    else:
        st.info("Bienvenue ! Choisissez une action dans le menu de gauche pour commencer.")
