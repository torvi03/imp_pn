import streamlit as st
from paie_app import analyse_bulletins
from ep5_app import analyse_missions
from attestation_app import analyse_attestation_nuitees
import pandas as pd

# --- Configuration de la page ---
st.set_page_config(page_title="Impôt Calc ✨", page_icon="✈️", layout="wide")

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

# --- COLONNE DE GAUCHE (MENU RÉORGANISÉ) ---
with col_gauche:
    st.header("🗂️ Actions")
    
    st.write("**1. Analyser les documents**")
    st.button("💵 Analyse des Bulletins de Paie", on_click=activer_menu, args=('paie',), use_container_width=True)
    st.button("✈️ Analyse des Rotations (EP5)", on_click=activer_menu, args=('ep5',), use_container_width=True)
    st.button("🏠 Analyse Attestation Nuitées", on_click=activer_menu, args=('attestation',), use_container_width=True)
    
    st.markdown("---")

    st.write("**2. Obtenir le résumé final**")
    st.button("SYNTHESE ANNUELLE", on_click=activer_synthese, use_container_width=True, type="primary")
    
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

# --- COLONNE DE DROITE (RÉSULTATS) ---
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
            st.subheader("🧮 Synthèse Annuelle Globale")
            
            res_paie = st.session_state.resultats_paie
            res_ep5 = st.session_state.resultats_ep5
            res_attest = st.session_state.resultats_attestation
            
            # --- NOUVEAU : Tableau de bord de vérification ---
            st.markdown("**Vérification de la complétude des documents**")
            col_check1, col_check2 = st.columns(2)
            
            with col_check1:
                compte_paie = res_paie.get("mois_comptes", 0) if res_paie else 0
                st.write("Bulletins de Paie :")
                if compte_paie == 12:
                    st.success(f"✅ {compte_paie}/12 mois complets")
                else:
                    st.warning(f"⚠️ {compte_paie}/12 mois détectés")
                st.progress(compte_paie / 12)

            with col_check2:
                compte_ep5 = res_ep5.get("mois_comptes", 0) if res_ep5 else 0
                st.write("Fichiers EP5 :")
                if compte_ep5 == 12:
                    st.success(f"✅ {compte_ep5}/12 mois complets")
                else:
                    st.warning(f"⚠️ {compte_ep5}/12 mois détectés")
                st.progress(compte_ep5 / 12)
            st.markdown("---")
            
            st.markdown("**Résumé financier**")
            total_paie = res_paie.get("total_general", 0.0) if res_paie else 0.0
            total_ep5 = res_ep5.get("total_indemnites", 0.0) if res_ep5 else 0.0
            total_attestation = sum(res_attest["resultats"].values()) if res_attest and res_attest.get("resultats") else 0.0
            grand_total = total_paie + total_ep5 + total_attestation
            
            if not any([res_paie, res_ep5, res_attest]):
                 st.warning("Aucune analyse n'a encore été effectuée. Veuillez lancer une analyse individuelle avant de demander la synthèse.")
            else:
                st.metric("💵 Total des indemnités de Paie", f"{total_paie:.2f} €", help="Calculé depuis la dernière analyse de paie.")
                st.metric("✈️ Total des indemnités de découcher (EP5)", f"{total_ep5:.2f} €", help="Calculé depuis la dernière analyse EP5.")
                st.metric("🏠 Total des frais d'hébergement (Attestations)", f"{total_attestation:.2f} €", help="Calculé depuis la dernière analyse d'attestations.")
                st.markdown("---")
                st.markdown(f"### 💰 Total Général à considérer : **{grand_total:.2f} €**")

    # --- AFFICHAGE DES RÉSULTATS DES ANALYSES INDIVIDUELLES ---
    elif st.session_state.menu_actif == 'paie' and st.session_state.resultats_paie:
        with st.container(border=True):
            res = st.session_state.resultats_paie
            st.subheader("💵 Synthèse des Bulletins de Paie")
            df = res.get("dataframe")
            if isinstance(df, pd.DataFrame) and not df.empty:
                st.dataframe(df, hide_index=True, use_container_width=True)
                csv_data = convert_df_to_csv(df)
                st.download_button("📥 Télécharger la synthèse (CSV)", csv_data, "synthese_paie.csv", 'text/csv')
            else:
                st.info("Aucune donnée extraite.")

    elif st.session_state.menu_actif == 'ep5' and st.session_state.resultats_ep5:
        with st.container(border=True):
            res = st.session_state.resultats_ep5
            st.subheader("✈️ Synthèse des Rotations (EP5)")
            if res.get("has_results"):
                st.metric(f"💰 Total Indemnités pour {res.get('annee_predominante', 'N/A')}", f"{res.get('total_indemnites', 0.0):.2f} EUR")
                tab1, tab2 = st.tabs(["📅 Rotations", "✈️ Stats Avions"])
                with tab1:
                    df_rot = res.get("rotations_df", pd.DataFrame())
                    st.dataframe(df_rot, hide_index=True, use_container_width=True)
                    if not df_rot.empty:
                        csv_data = convert_df_to_csv(df_rot)
                        st.download_button("📥 Télécharger les rotations (CSV)", csv_data, f"rotations_{res.get('annee_predominante')}.csv", 'text/csv')
                with tab2:
                    st.write("**Statistiques par Type d'Avion :**")
                    df_types = res.get("stats_avions_type_df", pd.DataFrame())
                    if not df_types.empty:
                        st.bar_chart(df_types.set_index('Type Avion'))
                    
                    st.write("**Statistiques par Immatriculation :**")
                    df_immats = res.get("stats_avions_immat_df", pd.DataFrame())
                    if not df_immats.empty:
                        st.bar_chart(df_immats.set_index('Immatriculation'))
            else:
                st.warning("Aucune rotation trouvée.")

    elif st.session_state.menu_actif == 'attestation' and st.session_state.resultats_attestation:
        with st.container(border=True):
            res = st.session_state.resultats_attestation
            st.subheader("🏠 Synthèse des Attestations")
            if res.get("resultats"):
                for annee, montant in res["resultats"].items():
                    st.metric(f"Frais Hébergement {annee}", f"{montant:.2f} €")
            else:
                st.info("Aucune attestation trouvée.")
    
    elif not st.session_state.show_synthese:
        st.info("Bienvenue ! Choisissez une action dans le menu de gauche pour commencer.")
