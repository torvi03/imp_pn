import streamlit as st
import pdfplumber
import re
from datetime import date, timedelta, time, datetime 
import pandas as pd 
import os

BASES_FR = ["CDG", "ORY"]

# --- CHARGEMENT DES DONNÉES AÉROPORT ---
@st.cache_data 
def load_airport_data_from_csv(csv_filepath):
    airport_data_dict = {}
    try:
        df = pd.read_csv(csv_filepath, delimiter=';', dtype=str, keep_default_na=False)
        required_cols = ['iata_code', 'municipality', 'iso_country', 'name'] 
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"Colonnes manquantes dans '{csv_filepath}': {', '.join(missing_cols)}")
            return {} 
        for index, row in df.iterrows():
            iata_raw = row.get('iata_code', ''); ville_raw = row.get('municipality', ''); 
            pays_iso_raw = row.get('iso_country', ''); nom_aeroport_raw = row.get('name', '')
            iata_cleaned = str(iata_raw).strip().upper()
            if iata_cleaned: 
                ville_val = str(ville_raw).strip() if str(ville_raw).strip() else "N/A"
                pays_val = str(pays_iso_raw).strip() if str(pays_iso_raw).strip() else "N/A"
                nom_aeroport_val = str(nom_aeroport_raw).strip() if str(nom_aeroport_raw).strip() else "N/A"
                airport_data_dict[iata_cleaned] = {
                    "ville": ville_val, 
                    "pays": pays_val,
                    "nom_aeroport": nom_aeroport_val
                }
    except FileNotFoundError:
        st.error(f"Fichier aéroport '{csv_filepath}' introuvable. Vérifiez le chemin et le montage de Drive.")
    except Exception as e:
        st.error(f"Erreur chargement CSV aéroport '{csv_filepath}': {e}")
    return airport_data_dict

CHEMIN_CSV_AIRPORTS_DRIVE = "airport-codes.csv" 
AIRPORT_DATA = load_airport_data_from_csv(CHEMIN_CSV_AIRPORTS_DRIVE)
if not AIRPORT_DATA: 
    st.warning("Données aéroport de secours utilisées.")
    AIRPORT_DATA = { 
        "CDG": {"ville": "Paris", "pays": "FR", "nom_aeroport": "Charles de Gaulle"}, 
        "ORY": {"ville": "Paris", "pays": "FR", "nom_aeroport": "Orly"},
        "JFK": {"ville": "New York", "pays": "US", "nom_aeroport": "John F. Kennedy"}, 
        "EWR": {"ville": "New York", "pays": "US", "nom_aeroport": "Newark Liberty"},
        "YUL": {"ville": "Montreal", "pays": "CA", "nom_aeroport": "Montréal-Trudeau"},
        "YYZ": {"ville": "Toronto", "pays": "CA", "nom_aeroport": "Toronto Pearson"},
        "YVR": {"ville": "Vancouver", "pays": "CA", "nom_aeroport": "Vancouver International"},
        "NRT": {"ville": "Tokyo", "pays": "JP", "nom_aeroport": "Narita"},
        "HND": {"ville": "Tokyo", "pays": "JP", "nom_aeroport": "Haneda"},
        "LFW": {"ville": "Lome", "pays": "TG", "nom_aeroport": "Lomé-Tokoin"},
        "ABV": {"ville": "Abuja", "pays": "NG", "nom_aeroport": "Nnamdi Azikiwe"},
        "LOS": {"ville": "Lagos", "pays": "NG", "nom_aeroport": "Murtala Muhammed"},
        "PHC": {"ville": "Port Harcourt", "pays": "NG", "nom_aeroport": "Port Harcourt"},
        "ICN": {"ville": "Séoul", "pays": "KR"}, "EZE": {"ville": "Buenos Aires", "pays": "AR"},
        "AEP": {"ville": "Buenos Aires", "pays": "AR"}, "FDF": {"ville": "Fort-de-France", "pays": "MQ"}
    }

def get_dgfip_code_for_escale(iata_code, ville, pays_iso):
    tax_code = pays_iso 
    if pays_iso == "JP" and ville == "Tokyo": tax_code = "TY"
    elif iata_code == 'EWR' or (pays_iso == "US" and ville == "New York"): tax_code = "NY"
    elif iata_code in ['YTZ', 'YKZ', 'YYZ']: tax_code = "VT"
    elif iata_code in ['CXH', 'YVR']: tax_code = "VV"
    elif iata_code == 'LFW': tax_code = "VL"
    elif iata_code in ["ABV", "LOS", "PHC"]: tax_code = "NV"
    return tax_code

@st.cache_data 
def load_indemnity_data(annee_str):
    nom_fichier_indemnites = f"dgfip_indemnites_{annee_str}.csv"
    chemin_fichier_indemnites = nom_fichier_indemnites
    if not os.path.exists(chemin_fichier_indemnites):
        chemin_fichier_indemnites_alt = f"../{nom_fichier_indemnites}" 
        if os.path.exists(chemin_fichier_indemnites_alt):
            chemin_fichier_indemnites = chemin_fichier_indemnites_alt
        else:
            st.warning(f"Fichier d'indemnités pour {annee_str} introuvable dans 'impot_calc/' ou '../'.")
            return {}
    indemnities_data = {}
    try:
        df = pd.read_csv(chemin_fichier_indemnites, delimiter=';')
        col_code_pays_dgfip = "Code Pays"; col_date_validite = "Date Validité Barème"; col_montant_eur = "Montant Barème (EUR)"
        required_cols = [col_code_pays_dgfip, col_date_validite, col_montant_eur]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"Colonnes manquantes dans '{chemin_fichier_indemnites}': {', '.join(missing_cols)}"); return indemnities_data
        for index, row in df.iterrows():
            code_dgfip = str(row[col_code_pays_dgfip]).strip().upper()
            date_validite_str = str(row[col_date_validite]).strip()
            montant_eur_str = str(row[col_montant_eur]).strip()
            try:
                date_validite = datetime.strptime(date_validite_str, "%Y-%m-%d").date()
                montant_eur = float(montant_eur_str) if montant_eur_str not in ["N/A", "Erreur Calc."] else 0.0
                if code_dgfip not in indemnities_data: indemnities_data[code_dgfip] = []
                indemnities_data[code_dgfip].append({"date_validite": date_validite, "montant_eur": montant_eur})
            except ValueError: continue 
        for code_p, liste_baremes in indemnities_data.items():
            liste_baremes.sort(key=lambda x: x["date_validite"], reverse=True)
        if indemnities_data: st.success(f"Indemnités pour {annee_str} chargées ({len(indemnities_data)} codes) depuis '{chemin_fichier_indemnites}'.")
    except Exception as e: st.error(f"Erreur chargement indemnités '{chemin_fichier_indemnites}': {e}"); import traceback; st.error(f"Trace: {traceback.format_exc()}")
    return indemnities_data

def find_applicable_indemnity(code_dgfip_ou_iso, target_date_obj, indemnity_data_source):
    if not indemnity_data_source or code_dgfip_ou_iso not in indemnity_data_source: return 0.0 
    baremes_pour_code = indemnity_data_source[code_dgfip_ou_iso] 
    for bareme in baremes_pour_code:
        if bareme["date_validite"] <= target_date_obj: return bareme["montant_eur"]
    return 0.0 

def convertir_ep5_heure_en_objet_temps(heure_ep5_str):
    try:
        if '.' in heure_ep5_str: h_str,c_str=heure_ep5_str.split('.',1);return(int(h_str),int(c_str.ljust(2,'0'))) 
        else: return (int(heure_ep5_str),0)
    except ValueError: return (0,0)

def calculer_date_segment(jour_str,ref_annee,ref_mois,date_depart_segment_pour_calcul_arrivee=None):
    try: jour=int(jour_str)
    except ValueError: raise 
    annee_calc=ref_annee; mois_calc=ref_mois
    if date_depart_segment_pour_calcul_arrivee: 
        annee_calc=date_depart_segment_pour_calcul_arrivee.year; mois_calc=date_depart_segment_pour_calcul_arrivee.month
        if jour < date_depart_segment_pour_calcul_arrivee.day: 
            mois_calc+=1
            if mois_calc > 12: mois_calc=1; annee_calc+=1
    try: return date(annee_calc,mois_calc,jour)
    except ValueError: raise

pattern_ep5_line = re.compile(
    r"^\s*\d+\s+"r"([A-Z0-9-]+)\s+"r"([A-Z0-9]+)\s+"r"([A-Z0-9]+)\s+"r"([A-Z]{3})\s+"
    r"(\d{1,2})\s*\|\s*(\d{1,2}\.\d{2,3})\s+"r"([A-Z]{3})\s+"r"(\d{1,2})\s*\|\s*(\d{1,2}\.\d{2,3})"          
)

def analyser_page_ep5(texte_page_ep5,annee_base,mois_base,nom_fichier):
    segments_extraits=[]
    lignes=texte_page_ep5.split('\n')
    for ligne_idx,ligne in enumerate(lignes):
        ligne_traitee=ligne.strip()
        if not ligne_traitee: continue
        match=pattern_ep5_line.search(ligne_traitee) 
        if match:
            try:
                avion_type_seg=match.group(1); avion_immat_seg=match.group(2)
                dep_airport_seg=match.group(4); dep_jour_seg_str=match.group(5).zfill(2) 
                dep_heure_ep5_str=match.group(6); arr_airport_seg=match.group(7)
                arr_jour_seg_str=match.group(8).zfill(2); arr_heure_ep5_str=match.group(9) 
                date_depart_seg=calculer_date_segment(dep_jour_seg_str,annee_base,mois_base)
                date_arrivee_seg=calculer_date_segment(arr_jour_seg_str,annee_base,mois_base,date_depart_segment_pour_calcul_arrivee=date_depart_seg)
                heure_depart_obj=convertir_ep5_heure_en_objet_temps(dep_heure_ep5_str)
                segments_extraits.append({'avion_type':avion_type_seg,'avion_immat':avion_immat_seg,
                    'dep_airport':dep_airport_seg,'dep_date':date_depart_seg,
                    'dep_heure_obj':heure_depart_obj,'arr_airport':arr_airport_seg,
                    'arr_date':date_arrivee_seg,'ligne_source_idx':ligne_idx,'nom_fichier':nom_fichier})
            except Exception as e: pass 
    if segments_extraits: segments_extraits.sort(key=lambda s:(s['dep_date'],s['dep_heure_obj']))
    rotations_trouvees=[]; en_rotation_active=False
    date_debut_rotation_actuelle=None; itineraire_en_cours=[] 
    segments_rotation_actuelle=[] 
    for segment in segments_extraits:
        if not en_rotation_active:
            if segment['dep_airport'] in BASES_FR:
                en_rotation_active=True; date_debut_rotation_actuelle=segment['dep_date']
                itineraire_en_cours=[segment['dep_airport'],segment['arr_airport']]
                segments_rotation_actuelle=[segment] 
        else: 
            itineraire_en_cours.append(segment['arr_airport']) 
            segments_rotation_actuelle.append(segment) 
            if segment['arr_airport'] in BASES_FR:
                date_fin_rotation_actuelle=segment['arr_date']
                if date_debut_rotation_actuelle and date_fin_rotation_actuelle >= date_debut_rotation_actuelle :
                    duree_jours=(date_fin_rotation_actuelle - date_debut_rotation_actuelle).days + 1
                    itineraire_simplifie=[]
                    if itineraire_en_cours:
                        itineraire_simplifie.append(itineraire_en_cours[0])
                        for i in range(1,len(itineraire_en_cours)):
                            if itineraire_en_cours[i] != itineraire_en_cours[i-1]: itineraire_simplifie.append(itineraire_en_cours[i])
                    rotations_trouvees.append({"Départ":date_debut_rotation_actuelle,"Retour":date_fin_rotation_actuelle,
                        "Durée":duree_jours,"Fichier":nom_fichier,"Itinéraire_aéroports":itineraire_simplifie,
                        "Segments_details":list(segments_rotation_actuelle)})
                en_rotation_active=False; date_debut_rotation_actuelle=None; itineraire_en_cours=[]; segments_rotation_actuelle=[]
    return rotations_trouvees,segments_extraits

def analyse_missions(uploaded_files):
    toutes_les_rotations = []; tous_les_segments = [] 
    indemnity_data_par_annee = {} 

    for idx_f, uploaded_file in enumerate(uploaded_files):
        annee_fichier_base = 0; mois_fichier_base = 0; nom_fichier_lower = uploaded_file.name.lower()
        match_date_pattern1 = re.search(r"(\d{2})(\d{4}|\d{2})", nom_fichier_lower)
        if match_date_pattern1:
            group1=match_date_pattern1.group(1); group2=match_date_pattern1.group(2)
            try:
                mois_candidat=int(group1)
                if 1<=mois_candidat<=12:
                    if len(group2)==4: annee_fichier_base=int(group2); mois_fichier_base=mois_candidat
                    elif len(group2)==2: annee_fichier_base=int(f"20{group2}"); mois_fichier_base=mois_candidat
            except ValueError: pass
        if not (1<=mois_fichier_base<=12 and annee_fichier_base > 1990):
            match_date_pattern2 = re.search(r"(\d{4}|\d{2})(\d{2})", nom_fichier_lower)
            if match_date_pattern2:
                group1=match_date_pattern2.group(1); group2=match_date_pattern2.group(2)
                try:
                    mois_candidat=int(group2)
                    if 1<=mois_candidat<=12:
                        if len(group1)==4: annee_fichier_base=int(group1); mois_fichier_base=mois_candidat
                        elif len(group1)==2: annee_fichier_base=int(f"20{group1}"); mois_fichier_base=mois_candidat
                except ValueError: pass
        if not (1<=mois_fichier_base<=12 and annee_fichier_base > 1990): 
            try:
                with pdfplumber.open(uploaded_file) as pdf_content_for_date:
                    texte_pour_date = ""
                    for i_page, page_content in enumerate(pdf_content_for_date.pages):
                        if i_page < 3: 
                            texte_page = page_content.extract_text() # Alignement correct ici
                            if texte_page:                           # Alignement correct ici
                                texte_pour_date += texte_page + "\n" 
                        else: 
                            break                                    # Alignement correct ici
                    if texte_pour_date:
                        month_year_match = re.search(r"Mois\s*:\s*([A-ZÉÛ]+)\s*(\d{4})", texte_pour_date, re.IGNORECASE)
                        if month_year_match:
                            nom_mois_fr = month_year_match.group(1).upper(); annee_fichier_base = int(month_year_match.group(2))
                            mois_map_fr = {"JANVIER":1,"FÉVRIER":2,"FEVRIER":2,"MARS":3,"AVRIL":4,"MAI":5,"JUIN":6,"JUILLET":7,"AOÛT":8,"AOUT":8,"SEPTEMBRE":9,"OCTOBRE":10,"NOVEMBRE":11,"DÉCEMBRE":12,"DECEMBRE":12}
                            if nom_mois_fr in mois_map_fr: mois_fichier_base = mois_map_fr[nom_mois_fr]
            except Exception: pass 
        if not (1<=mois_fichier_base<=12 and annee_fichier_base > 1990):
            st.warning(f"Date PDF invalide pour '{uploaded_file.name}'. Ignoré."); continue
        
        annee_actuelle_du_pdf = str(annee_fichier_base)
        if annee_actuelle_du_pdf not in indemnity_data_par_annee:
            indemnity_data_par_annee[annee_actuelle_du_pdf] = load_indemnity_data(annee_actuelle_du_pdf)
        
        try:
            with pdfplumber.open(uploaded_file) as pdf:
                num_pages_ep5_trouvees = 0
                for page_num, page in enumerate(pdf.pages):
                    texte = page.extract_text() if page.extract_text() else "" 
                    if "EP5" in texte.upper(): 
                        num_pages_ep5_trouvees += 1
                        rotations_page, segments_page = analyser_page_ep5(texte, annee_fichier_base, mois_fichier_base, uploaded_file.name)
                        for r_p in rotations_page: r_p["Année_PDF"] = annee_actuelle_du_pdf
                        if rotations_page: toutes_les_rotations.extend(rotations_page)
                        if segments_page: tous_les_segments.extend(segments_page) 
                if num_pages_ep5_trouvees == 0 and uploaded_files: st.warning(f"Aucune page 'EP5' trouvée dans {uploaded_file.name}.")
        except Exception as e: st.error(f"Erreur analyse PDF {uploaded_file.name}: {e}"); continue
    
    if not toutes_les_rotations and not tous_les_segments and uploaded_files: 
        st.info("Aucune rotation ou segment de vol n'a pu être extrait."); return
    if not uploaded_files: return

    # Déterminer l'année prédominante pour l'affichage du total des indemnités
    annee_predominante_pour_affichage_total = None
    map_annee_fichiers_count = {}
    for r in toutes_les_rotations: # Utiliser toutes_les_rotations pour déterminer l'année prédominante
        annee_r = r.get("Année_PDF")
        if annee_r: map_annee_fichiers_count[annee_r] = map_annee_fichiers_count.get(annee_r, 0) + 1
    if map_annee_fichiers_count:
        annee_predominante_pour_affichage_total = max(map_annee_fichiers_count, key=map_annee_fichiers_count.get)
    
    total_indemnites_annee_affichee = 0.0
    if annee_predominante_pour_affichage_total and annee_predominante_pour_affichage_total in indemnity_data_par_annee:
        indemnity_data_annee_predominante = indemnity_data_par_annee[annee_predominante_pour_affichage_total]
        for r_calc in toutes_les_rotations:
            if r_calc.get("Année_PDF") == annee_predominante_pour_affichage_total:
                itin_aeroports_calc = r_calc.get("Itinéraire_aéroports", [])
                escale_principale_iata_calc = None
                if len(itin_aeroports_calc) > 1:
                    if itin_aeroports_calc[0] in BASES_FR:
                        if itin_aeroports_calc[1] not in BASES_FR: escale_principale_iata_calc = itin_aeroports_calc[1]
                        elif len(itin_aeroports_calc) > 2 and itin_aeroports_calc[1] in BASES_FR and itin_aeroports_calc[2] not in BASES_FR : escale_principale_iata_calc = itin_aeroports_calc[2]
                    elif itin_aeroports_calc[0] not in BASES_FR: escale_principale_iata_calc = itin_aeroports_calc[0]

                if escale_principale_iata_calc and escale_principale_iata_calc not in BASES_FR and indemnity_data_annee_predominante and AIRPORT_DATA:
                    airport_info_calc = AIRPORT_DATA.get(escale_principale_iata_calc.upper())
                    if airport_info_calc and airport_info_calc.get("pays") != "N/A":
                        code_recherche_calc = get_dgfip_code_for_escale(escale_principale_iata_calc, airport_info_calc.get("ville"), airport_info_calc.get("pays"))
                        indemnite_jour_calc = find_applicable_indemnity(code_recherche_calc, r_calc["Départ"], indemnity_data_annee_predominante)
                        total_indemnites_annee_affichee += indemnite_jour_calc * r_calc["Durée"]
    
    if annee_predominante_pour_affichage_total:
        col_g, col_c, col_d = st.columns([1,2,1]) 
        with col_c: 
            st.metric(label=f"💰 Total Indemnités Estimées pour {annee_predominante_pour_affichage_total}", 
                      value=f"{total_indemnites_annee_affichee:.2f} EUR")
        st.markdown("---")

    tab_rotations, tab_stats_avions = st.tabs(["📅 Tableau des Rotations", "✈️ Statistiques Avions"])
    with tab_rotations:
        st.subheader("Synthèse des Rotations")
        if toutes_les_rotations:
            rotations_uniques_liste = []
            set_rotations_vues = set()
            for r_val in toutes_les_rotations:
                rotation_id_tuple = (r_val["Départ"], r_val["Retour"], r_val["Durée"], tuple(r_val.get("Itinéraire_aéroports", [])), r_val.get("Année_PDF"))
                if rotation_id_tuple not in set_rotations_vues:
                    rotations_uniques_liste.append(r_val); set_rotations_vues.add(rotation_id_tuple)
            rotations_uniques_liste.sort(key=lambda r_sort: r_sort["Départ"])
            total_jours_mission_glob = sum(r['Durée'] for r in rotations_uniques_liste) # Renommé pour éviter conflit
            
            # Déplacer ces metrics ici si on veut les garder, ou les enlever si le total indemnité est prioritaire
            # col1_tab, col2_tab = st.columns(2); 
            # col1_tab.metric("Rotations Uniques (total fichiers)", len(rotations_uniques_liste)); 
            # col2_tab.metric("Total Jours Mission (total fichiers)", f"{total_jours_mission_glob} j"); 
            # st.markdown("---") 

            donnees_tableau = []
            for r_idx, r_disp in enumerate(rotations_uniques_liste):
                itineraire_str = " → ".join(r_disp.get("Itinéraire_aéroports", ["N/A"]))
                escale_principale_pour_affichage = "N/A"; total_indemnites_rotation_individuelle = 0.0 
                indemnite_journaliere_applicable_pour_affichage = 0.0
                annee_rotation_concernee = r_disp.get("Année_PDF")
                indemnity_data_specifique_annee = indemnity_data_par_annee.get(annee_rotation_concernee, {}) if annee_rotation_concernee else {}
                itin_aeroports = r_disp.get("Itinéraire_aéroports", [])
                escale_principale_iata = None
                if len(itin_aeroports) > 1:
                    if itin_aeroports[0] in BASES_FR:
                        if itin_aeroports[1] not in BASES_FR: escale_principale_iata = itin_aeroports[1]
                        elif len(itin_aeroports) > 2 and itin_aeroports[1] in BASES_FR and itin_aeroports[2] not in BASES_FR : escale_principale_iata = itin_aeroports[2]
                    elif itin_aeroports[0] not in BASES_FR: escale_principale_iata = itin_aeroports[0]
                
                if escale_principale_iata and indemnity_data_specifique_annee and AIRPORT_DATA:
                    airport_info = AIRPORT_DATA.get(escale_principale_iata.upper())
                    if airport_info and airport_info.get("pays") != "N/A":
                        code_recherche_indemnite = get_dgfip_code_for_escale(escale_principale_iata, airport_info.get("ville"), airport_info.get("pays"))
                        if code_recherche_indemnite != airport_info.get("pays") and code_recherche_indemnite in indemnity_data_specifique_annee:
                            escale_principale_pour_affichage = f"{airport_info.get('ville', escale_principale_iata)} ({code_recherche_indemnite})"
                        else: escale_principale_pour_affichage = f"{airport_info.get('ville', escale_principale_iata)} ({airport_info.get('pays', 'N/A')})"
                        indemnite_journaliere_applicable_pour_affichage = find_applicable_indemnity(code_recherche_indemnite, r_disp["Départ"], indemnity_data_specifique_annee)
                        if escale_principale_iata not in BASES_FR : 
                                 total_indemnites_rotation_individuelle = indemnite_journaliere_applicable_pour_affichage * r_disp["Durée"]
                    else: escale_principale_pour_affichage = f"{escale_principale_iata} (Infos Pays N/A)"
                elif escale_principale_iata and escale_principale_iata in BASES_FR: escale_principale_pour_affichage = "En base / Vol local"
                
                donnees_tableau.append({
                    "Mois Départ": r_disp["Départ"].strftime("%B %Y"), "Jour Dép.": r_disp["Départ"].day,
                    "Jour Ret.": r_disp["Retour"].day, "Itinéraire Global": itineraire_str,
                    "Escale Principale": escale_principale_pour_affichage, 
                    "Indemnité/jour Réf. (EUR)": f"{indemnite_journaliere_applicable_pour_affichage:.2f}" if indemnite_journaliere_applicable_pour_affichage > 0.005 else "N/A",
                    "Durée (j)": r_disp["Durée"],
                    "Indemnité Tot. (EUR)": f"{total_indemnites_rotation_individuelle:.2f}" if total_indemnites_rotation_individuelle > 0.005 else "N/A"
                })
            if donnees_tableau:
                df_rotations = pd.DataFrame(donnees_tableau)
                colonnes_ordre = ["Mois Départ", "Jour Dép.", "Jour Ret.", "Itinéraire Global", "Escale Principale", "Indemnité/jour Réf. (EUR)", "Durée (j)", "Indemnité Tot. (EUR)"]
                df_rotations = df_rotations[colonnes_ordre]
                st.dataframe(df_rotations, hide_index=True, use_container_width=True)
        else: st.info("Aucune rotation détectée.")
    with tab_stats_avions: 
        st.subheader("Statistiques sur les Avions Utilisés (par segment de vol)")
        if tous_les_segments: 
            types_avion = {}; immats_avion = {}
            for seg in tous_les_segments:
                types_avion[seg['avion_type']] = types_avion.get(seg['avion_type'], 0) + 1
                immats_avion[seg['avion_immat']] = immats_avion.get(seg['avion_immat'], 0) + 1
            col_type_stats, col_immat_stats = st.columns(2) # Noms de variables différents pour colonnes Streamlit
            with col_type_stats:
                st.write("**Par Type d'Avion :**")
                if types_avion:
                    df_types = pd.DataFrame(list(types_avion.items()), columns=['Type Avion', 'Nombre de Segments'])
                    df_types = df_types.sort_values(by='Nombre de Segments', ascending=False)
                    st.bar_chart(df_types.set_index('Type Avion'), height=300)
                else: st.write("Aucune donnée de type d'avion.")
            with col_immat_stats:
                st.write("**Par Immatriculation :**")
                if immats_avion:
                    df_immats = pd.DataFrame(list(immats_avion.items()), columns=['Immatriculation', 'Nombre de Segments'])
                    df_immats = df_immats.sort_values(by='Nombre de Segments', ascending=False)
                    st.bar_chart(df_immats.set_index('Immatriculation'), height=300)
                else: st.write("Aucune donnée d'immatriculation.")
        else: st.info("Aucun segment de vol n'a été extrait pour générer des statistiques sur les avions.")
