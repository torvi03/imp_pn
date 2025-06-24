import streamlit as st
from paie_app import analyse_bulletins
from ep5_app import analyse_missions
from attestation_app import analyse_attestation_nuitees

# Configuration de la page
st.set_page_config(
    page_title="Impôt Calc ✨",
    page_icon="✈️", # Changé pour un emoji plus pertinent
    layout="wide",
    initial_sidebar_state="collapsed" # On n'utilise plus la sidebar
)

# --- Initialisation de l'état de la session ---
if 'menu_actif' not in st.session_state:
    st.session_state.menu_actif = None # 'paie', 'ep5', 'attestation'

# --- Fonctions pour changer le menu actif ---
def activer_menu(menu):
    st.session_state.menu_actif = menu

# --- PAGE PRINCIPALE ---
st.title("📊 Assistant de Comptabilité de Vol")
st.markdown("---")

# Créer deux colonnes principales
col_gauche, col_droite = st.columns([1, 2]) # Colonne de gauche plus petite

# --- COLONNE DE GAUCHE (Contrôles) ---
with col_gauche:
    st.header("🗂️ Analyses Disponibles")
    st.write("Cliquez sur une analyse pour téléverser les fichiers correspondants.")
    
    # Boutons pour choisir l'analyse
    st.button("💵 Analyse des Bulletins de Paie", on_click=activer_menu, args=('paie',), use_container_width=True)
    st.button("✈️ Analyse des Rotations (EP5)", on_click=activer_menu, args=('ep5',), use_container_width=True)
    st.button("🏠 Analyse Attestation Nuitées", on_click=activer_menu, args=('attestation',), use_container_width=True)

    st.markdown("---")

    # Afficher l'uploader de fichiers en fonction du menu actif
    fichiers_analyses = None
    if st.session_state.menu_actif == 'paie':
        with st.container(border=True): # Encadrer l'uploader pour le mettre en valeur
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
                "Sélectionnez les PDF contenant les attestations annuelles (généralement Février) :", type="pdf",
                accept_multiple_files=True, key="attestation_uploader"
            )

# --- COLONNE DE DROITE (Résultats) ---
with col_droite:
    st.header("📈 Résultats de l'Analyse")

    # Initialiser les conteneurs pour les résultats
    # Cela permet de les afficher même si l'analyse d'un autre type est lancée après
    if 'resultats_paie' not in st.session_state:
        st.session_state.resultats_paie = None
    if 'resultats_ep5' not in st.session_state:
        st.session_state.resultats_ep5 = None
    
    # Lancer l'analyse si des fichiers ont été téléversés
    if fichiers_analyses:
        with st.spinner(f"Analyse de {len(fichiers_analyses)} fichier(s) en cours... ⏳"):
            if st.session_state.menu_actif == 'paie':
                # Stocker le résultat retourné
                st.session_state.resultats_paie = analyse_bulletins(fichiers_analyses)
            elif st.session_state.menu_actif == 'ep5':
                # analyse_missions affiche déjà tout, donc pas besoin de stocker un retour pour l'instant
                analyse_missions(fichiers_analyses)
                st.balloons()
            elif st.session_state.menu_actif == 'attestation':
                # La fonction analyse_attestation_nuitees affiche directement les résultats,
                # on pourrait la modifier pour qu'elle retourne les données si on veut les stocker aussi
                analyse_attestation_nuitees(fichiers_analyses)

    # Afficher les résultats stockés
    if st.session_state.resultats_paie:
        # Cet affichage est maintenant dans impot_calc.py au lieu de paie_app.py
        # Il sera dans la colonne de droite comme vous le vouliez.
        with col_droite: # En supposant que vous avez défini col_gauche, col_droite
             with st.container(border=True):
                st.subheader("💵 Total des Indemnités (Paie)")
                total_paie = st.session_state.resultats_paie.get("total_general", 0.0)
                st.metric("Total général extrait des bulletins", f"{total_paie:.2f} €")
                with st.expander("Voir le détail des totaux par catégorie"):
                    for cle, montant in st.session_state.resultats_paie.get("totaux_par_cle", {}).items():
                        st.write(f"{cle}: {montant:.2f} €")
            
    if st.session_state.resultats_ep5:
        with st.container(border=True):
            st.subheader("✈️ Tableau des Rotations")
            # La fonction analyse_missions affiche déjà le tableau et les stats.
            # Elle n'a pas besoin de retourner quoi que ce soit si elle affiche elle-même ses résultats.
            # La logique d'affichage est déjà dans ep5_app.py
            pass # L'affichage est déjà géré par l'appel à analyse_missions

    if not st.session_state.resultats_paie and not st.session_state.resultats_ep5:
        if st.session_state.menu_actif:
            st.info("Les résultats s'afficheront ici après l'analyse des fichiers téléversés.")
        else:
            st.info("Veuillez choisir une analyse et téléverser des fichiers.")
