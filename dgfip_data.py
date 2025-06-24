import requests
import re 
import json 
from datetime import datetime, date 
import csv 
import os

# URLs de la DGFiP
WEBPAYS_URL = "https://www.economie.gouv.fr/dgfip/fichiers_taux_chancellerie/txt/Webpays"
WEBMISS_URL = "https://www.economie.gouv.fr/dgfip/fichiers_taux_chancellerie/txt/Webmiss"
WEBTAUX_URL = "https://www.economie.gouv.fr/dgfip/fichiers_taux_chancellerie/txt/Webtaux"

# --- CONFIGURATION SPÉCIFIQUE ---
PAYS_INITIAUX_ET_CORRECTIONS = {
    "US": {"n": "ÉTATS-UNIS (GÉNÉRAL)", "a": []}, 
    "CA": {"n": "CANADA (GÉNÉRAL)", "a": []},
    "JP": {"n": "JAPON (GÉNÉRAL)", "a": []}, 
    "TG": {"n": "TOGO", "a": []}, 
    "NG": {"n": "NIGERIA", "a": []},
    "NY": {"n": "NEW YORK CITY (USA)", "a": [], "is_specific_rate_location": True, "parent_iso_country": "US"},
    "VT": {"n": "TORONTO (CANADA)", "a": [], "is_specific_rate_location": True, "parent_iso_country": "CA"},
    "VV": {"n": "VANCOUVER (CANADA)", "a": [], "is_specific_rate_location": True, "parent_iso_country": "CA"},
    "TY": {"n": "TOKYO (JAPON)", "a": [], "is_specific_rate_location": True, "parent_iso_country": "JP"},
    "VL": {"n": "LOMÉ (TOGO)", "a": [], "is_specific_rate_location": True, "parent_iso_country": "TG"},
    "NV": {"n": "ABUJA/LAGOS/PORT HARCOURT (NIGERIA)", "a": [], "is_specific_rate_location": True, "parent_iso_country": "NG"},
    "DE": {"n": "ALLEMAGNE", "a": []}, "AT": {"n": "AUTRICHE", "a": []},
    "BE": {"n": "BELGIQUE", "a": []}, "CY": {"n": "CHYPRE", "a": []},
    "ES": {"n": "ESPAGNE", "a": []}, "FI": {"n": "FINLANDE", "a": []},
    "FR": {"n": "FRANCE MÉTROPOLITAINE", "a": [], "type": "FORFAIT_EU_CIBLE"}, 
    "GR": {"n": "GRÈCE", "a": []}, "IE": {"n": "IRLANDE", "a": []},
    "IT": {"n": "ITALIE", "a": []}, "LU": {"n": "LUXEMBOURG", "a": []},
    "MT": {"n": "MALTE", "a": []}, "NL": {"n": "PAYS-BAS", "a": []},
    "PT": {"n": "PORTUGAL", "a": []}, "SK": {"n": "SLOVAQUIE", "a": []},
    "SI": {"n": "SLOVÉNIE", "a": []}, "HR": {"n": "CROATIE", "a": []}, 
    "EE": {"n": "ESTONIE", "a": []}, "LV": {"n": "LETTONIE", "a": []}, 
    "LT": {"n": "LITUANIE", "a": []},
    "GP": {"n": "GUADELOUPE", "a": [], "type": "FORFAIT_EU_CIBLE"},
    "MQ": {"n": "MARTINIQUE", "a": [], "type": "FORFAIT_EU_CIBLE"},
    "GF": {"n": "GUYANE", "a": [], "type": "FORFAIT_EU_CIBLE"},
    "RE": {"n": "LA RÉUNION", "a": [], "type": "FORFAIT_EU_CIBLE"},
    "YT": {"n": "MAYOTTE", "a": [], "type": "FORFAIT_EU_CIBLE"},
    "PM": {"n": "SAINT-PIERRE-ET-MIQUELON", "a": [], "type": "FORFAIT_EU_CIBLE"},
    "MF": {"n": "SAINT-MARTIN (PARTIE FRANÇAISE)", "a": [], "type": "FORFAIT_EU_CIBLE"},
    "BL": {"n": "SAINT-BARTHÉLEMY", "a": [], "type": "FORFAIT_EU_CIBLE"},
    "SX": {"n": "SAINT-MARTIN (PARTIE NÉERLANDAISE)", "a": []}, 
    "CD": {"n": "CONGO (RÉP. DÉMOCRATIQUE DU)", "a": []}, 
    "CF": {"n": "RÉPUBLIQUE CENTRAFRICAINE", "a": []},
    "CZ": {"n": "TCHÉQUIE", "a": []}, 
    "DO": {"n": "RÉPUBLIQUE DOMINICAINE", "a": []},
}
MAPPING_CODES_DGFiP_VERS_STOCKAGE = {k:k for k in ["NY", "VT", "VV", "TY", "VL", "NV"]} # S'assurer que ces codes sont utilisés tels quels
PAYS_EUROPE_POUR_MOYENNE = ["DE","AT","BE","CY","ES","FI","FR","GR","IE","IT","LU","MT","NL","PT","SK","SI","HR","EE","LV","LT"]
PAYS_CIBLES_FORFAIT_MOYEN_EU = ["FR","YT","PM","GP","MQ","GF","RE","SX","MF","BL"]
INDEMNITES_MANUELLES_SPECIFIQUES = {} 
# --- FIN CONFIGURATION SPÉCIFIQUE ---

def telecharger_fichier_dgfip(url):
    print(f"Tentative de téléchargement de : {url}")
    try:
        response = requests.get(url, timeout=10); response.raise_for_status() 
        try: text_content = response.content.decode('utf-8'); print(f"  > Fichier décodé avec utf-8."); return text_content
        except UnicodeDecodeError:
            print(f"  > Échec utf-8, autres encodages..."); encodings_to_try = ['latin-1', 'cp1252']
            for enc in encodings_to_try:
                try: text_content = response.content.decode(enc); print(f"  > Fichier décodé avec {enc}."); return text_content
                except UnicodeDecodeError: print(f"  > Échec avec {enc}...")
            print(f"  > ERREUR : Impossible de décoder {url}."); return response.text
    except requests.exceptions.Timeout: print(f"ERREUR téléchargement {url}: Timeout."); return None
    except requests.exceptions.RequestException as e: print(f"ERREUR téléchargement {url}: {e}"); return None

def traiter_webpays(contenu_webpays, donnees_pays_initiales):
    pays_data = {k: v.copy() for k, v in donnees_pays_initiales.items()} 
    if not contenu_webpays: print("  > Contenu Webpays vide."); return pays_data
    print("\n--- Début du traitement de Webpays (enrichissement) ---"); lignes = contenu_webpays.splitlines(); lignes_analysees_count = 0
    for i, ligne in enumerate(lignes):
        ligne_traitee = ligne.strip();
        if not ligne_traitee: continue
        parts = ligne_traitee.split('\t') 
        if len(parts) >= 3: 
            code_pays_brut = parts[0].strip(); nom_pays_brut_webpays = parts[2].strip() 
            code_a_utiliser = MAPPING_CODES_DGFiP_VERS_STOCKAGE.get(code_pays_brut, code_pays_brut)
            if code_a_utiliser and nom_pays_brut_webpays and code_a_utiliser not in ["BU", "EU", "MC", "PS", "XC"]:
                nom_pays_nettoye_webpays = re.sub(r'\s\([^)]+\)|^\s*-\s*', '', nom_pays_brut_webpays).strip()
                nom_pays_nettoye_webpays = re.sub(r'\s+', ' ', nom_pays_nettoye_webpays)
                if code_a_utiliser not in pays_data: 
                    pays_data[code_a_utiliser] = {"n": nom_pays_nettoye_webpays, "a": []} 
                    lignes_analysees_count +=1
                elif not pays_data[code_a_utiliser].get("n") or pays_data[code_a_utiliser].get("n") == code_a_utiliser : 
                    pays_data[code_a_utiliser]["n"] = nom_pays_nettoye_webpays
    print(f"--- Fin traitement Webpays. {lignes_analysees_count} codes pays potentiellement ajoutés/mis à jour. Total: {len(pays_data)}. ---")
    return pays_data

def formater_montant_webmiss(montant_str):
    if not montant_str or len(montant_str) < 4: return 0.0 
    partie_entiere_str = montant_str[:-4]; partie_decimale_str = montant_str[-4:]
    montant_avec_point = f"{partie_entiere_str}.{partie_decimale_str}"
    try: return float(montant_avec_point)
    except ValueError: return 0.0

def traiter_webmiss(contenu_webmiss, pays_data_existant, annee_actuelle_str, indemnites_manuelles_pour_annee):
    print("\n--- Début du traitement de Webmiss ---")
    if not contenu_webmiss: print("  > Contenu Webmiss vide."); 
    lignes = contenu_webmiss.splitlines() if contenu_webmiss else []
    barèmes_ajoutes_dgfip_count = 0
    for i, ligne in enumerate(lignes):
        ligne_traitee = ligne.strip();
        if not ligne_traitee: continue
        parts = ligne_traitee.split('\t')
        if len(parts) >= 5: 
            code_pays_brut_webmiss = parts[0].strip(); date_str = parts[1].strip()
            devise = parts[2].strip().upper(); montant_g1_str = parts[4].strip()
            if not code_pays_brut_webmiss or not date_str or not devise or not montant_g1_str: continue
            code_a_utiliser = MAPPING_CODES_DGFiP_VERS_STOCKAGE.get(code_pays_brut_webmiss, code_pays_brut_webmiss)
            try:
                date_obj = datetime.strptime(date_str, "%d/%m/%Y").date(); date_iso = date_obj.strftime("%Y-%m-%d")
                if date_obj.year > int(annee_actuelle_str) + 5: continue
                montant_final = formater_montant_webmiss(montant_g1_str)
                if code_a_utiliser not in pays_data_existant:
                    pays_data_existant[code_a_utiliser] = {"n": PAYS_INITIAUX_ET_CORRECTIONS.get(code_a_utiliser, {}).get("n", code_a_utiliser), "a": []}
                if "a" not in pays_data_existant[code_a_utiliser]: pays_data_existant[code_a_utiliser]["a"] = []
                pays_data_existant[code_a_utiliser]["a"].append([date_iso, devise, montant_final])
                barèmes_ajoutes_dgfip_count += 1
            except (ValueError, Exception): pass
            
    for code_pays_manuel, liste_baremes_manuels in indemnites_manuelles_pour_annee.items():
        cible_code_pays = MAPPING_CODES_DGFiP_VERS_STOCKAGE.get(code_pays_manuel, code_pays_manuel)
        if cible_code_pays not in pays_data_existant:
            pays_data_existant[cible_code_pays] = {"n": PAYS_INITIAUX_ET_CORRECTIONS.get(cible_code_pays, {}).get("n", cible_code_pays), "a": []}
        print(f"  > Application des barèmes manuels/forfait pour {cible_code_pays} (source: {code_pays_manuel})")
        pays_data_existant[cible_code_pays]["a"].extend(liste_baremes_manuels)

    for code_p, data_p in pays_data_existant.items():
        if "a" in data_p and data_p["a"]: 
            baremes_uniques = []; vus = set()
            for b_item in data_p["a"]: # Assurer que b_item est bien une liste/tuple avant de dépacker
                if isinstance(b_item, (list, tuple)) and len(b_item) == 3:
                    b_date, b_devise, b_montant = b_item
                    identifiant_bareme = (str(b_date), str(b_devise), float(b_montant)) 
                    if identifiant_bareme not in vus:
                        baremes_uniques.append([b_date, b_devise, b_montant]); vus.add(identifiant_bareme)
                # else: print(f"  Avertissement: Barème malformé ignoré pour {code_p}: {b_item}")
            baremes_uniques.sort(key=lambda x: (x[0], -float(x[2] if x[2] is not None else 0)), reverse=True) 
            data_p["a"] = baremes_uniques
    print(f"--- Fin traitement Webmiss. {barèmes_ajoutes_dgfip_count} barèmes DGFiP lus. Barèmes manuels/forfaits appliqués et listes triées/dédoublonnées. ---")
    return pays_data_existant

def formater_taux_webtaux(taux_str_brut):
    """
    Formate la chaîne de caractères du taux de Webtaux.
    La valeur formatée XXX.YYYYY est interprétée comme Devise/EUR.
    Cette fonction retourne le taux EUR/Devise (en faisant 1 / (Devise/EUR)).
    """
    if not taux_str_brut or len(taux_str_brut) < 3 : return None 
    partie1 = taux_str_brut[:3]; partie2 = taux_str_brut[3:]
    taux_avec_point = f"{partie1}.{partie2}"
    try: 
        valeur_directe_devise_par_eur = float(taux_avec_point) 
        if valeur_directe_devise_par_eur == 0: return None
        taux_eur_par_devise = 1.0 / valeur_directe_devise_par_eur # INVERSION ICI
        return taux_eur_par_devise
    except ValueError: return None

def traiter_webtaux(contenu_webtaux, annee_actuelle_str):
    taux_data = {}; print("\n--- Début du traitement de Webtaux ---") 
    if not contenu_webtaux: print("  > Contenu Webtaux vide."); return taux_data
    lignes = contenu_webtaux.splitlines(); taux_ajoutes_count = 0
    for i, ligne in enumerate(lignes):
        ligne_traitee = ligne.strip();
        if not ligne_traitee: continue
        parts = ligne_traitee.split('\t')
        if len(parts) >= 3:
            devise = parts[0].strip().upper(); date_str = parts[1].strip(); valeur_taux_brute_str = parts[2].strip()
            if not devise or not date_str or not valeur_taux_brute_str or devise == "ZWR": continue
            try:
                date_obj = datetime.strptime(date_str, "%d/%m/%Y").date(); date_iso = date_obj.strftime("%Y-%m-%d")
                if date_obj.year > int(annee_actuelle_str) + 5 : continue
                taux_eur_par_devise = formater_taux_webtaux(valeur_taux_brute_str) # Maintenant EUR/Devise
                if taux_eur_par_devise is not None:
                    if devise not in taux_data: taux_data[devise] = []
                    taux_data[devise].append([date_iso, taux_eur_par_devise]); taux_ajoutes_count += 1
            except (ValueError, Exception): pass
    for devise_k, liste_taux in taux_data.items(): liste_taux.sort(key=lambda x: x[0], reverse=True)
    print(f"--- Fin Webtaux. {taux_ajoutes_count} entrées. {len(taux_data)} devises (taux en EUR/Devise). ---"); return taux_data

def find_applicable_rate(liste_taux_par_date_eur_par_devise, date_cible_str): # Renommé pour clarté
    if not liste_taux_par_date_eur_par_devise: return None
    for date_taux_str, taux in liste_taux_par_date_eur_par_devise: 
        if date_taux_str <= date_cible_str: return taux
    return None

def calculer_taux_annuels(donnees_taux_historique_eur_par_devise, annee_str):
    taux_annuels = {}; date_debut_annee = f"{annee_str}-01-01"; date_fin_annee = f"{annee_str}-12-31"
    taux_annuels["EUR"] = [1.0, 1.0, 1.0]; 
    valeur_fixe_eur_pour_xaf_xof = 1.0 * 655.9570 # EUR/XOF ou EUR/XAF
    taux_fixes_eur_par_devise = {"XAF": valeur_fixe_eur_pour_xaf_xof, "XOF": valeur_fixe_eur_pour_xaf_xof}
    for devise_fixe, taux_fixe_eur_d in taux_fixes_eur_par_devise.items():
         taux_annuels[devise_fixe] = [taux_fixe_eur_d, taux_fixe_eur_d, taux_fixe_eur_d]
    for devise, liste_taux in donnees_taux_historique_eur_par_devise.items(): # liste_taux est en EUR/Devise
        if devise in taux_annuels: continue 
        taux_debut_eur_d = find_applicable_rate(liste_taux, date_debut_annee)
        taux_fin_eur_d = find_applicable_rate(liste_taux, date_fin_annee)   
        if taux_fin_eur_d is None and taux_debut_eur_d is not None: taux_fin_eur_d = taux_debut_eur_d
        elif taux_debut_eur_d is None and taux_fin_eur_d is not None: taux_debut_eur_d = taux_fin_eur_d
        if taux_debut_eur_d is not None and taux_fin_eur_d is not None:
            taux_moyen_eur_d = (taux_debut_eur_d + taux_fin_eur_d) / 2.0
            taux_annuels[devise] = [taux_debut_eur_d, taux_fin_eur_d, taux_moyen_eur_d]
        elif taux_debut_eur_d is not None: 
            taux_annuels[devise] = [taux_debut_eur_d, taux_debut_eur_d, taux_debut_eur_d]
        else:
            print(f"  Avertissement: Aucun taux EUR/Devise pour {devise} pour {annee_str}."); taux_annuels[devise] = [None,None,None] 
    print(f"\n--- Taux annuels (EUR/Devise) calculés pour {len(taux_annuels)} devises. ---"); return taux_annuels

def find_applicable_indemnity_for_date(baremes_pays_tries_par_date_recente, target_date_obj):
    if not baremes_pays_tries_par_date_recente: return None
    target_date_str = target_date_obj.strftime("%Y-%m-%d") 
    for bareme_item in baremes_pays_tries_par_date_recente:
        if isinstance(bareme_item, (list, tuple)) and len(bareme_item) == 3:
            date_bareme_str, devise_bareme, montant_bareme = bareme_item
            if isinstance(date_bareme_str, str) and date_bareme_str <= target_date_str: 
                return {"date_validite": date_bareme_str, "devise": devise_bareme, "montant": montant_bareme}
    return None

def calculer_moyenne_indemnites_europe(donnees_pays_complets, annee_str, liste_pays_europe_reference, taux_annuels_eur_par_devise):
    print(f"\n--- Calcul de l'indemnité moyenne européenne pour {annee_str} ---")
    moyennes_annuelles_par_pays_ref_eur = []
    for code_pays_ref in liste_pays_europe_reference:
        if code_pays_ref in donnees_pays_complets and donnees_pays_complets[code_pays_ref].get("a"):
            baremes_du_pays = donnees_pays_complets[code_pays_ref]["a"] 
            indemnites_mensuelles_pour_ce_pays_eur = []
            for mois in range(1, 13):
                date_test_mois = date(int(annee_str), mois, 15) 
                bareme_applicable_mois = find_applicable_indemnity_for_date(baremes_du_pays, date_test_mois)
                if bareme_applicable_mois:
                    montant_local = bareme_applicable_mois["montant"]
                    devise_locale = bareme_applicable_mois["devise"]
                    if devise_locale == "EUR":
                        indemnites_mensuelles_pour_ce_pays_eur.append(montant_local)
                    # Utiliser les taux EUR/Devise pour multiplier
                    elif devise_locale in taux_annuels_eur_par_devise and \
                       taux_annuels_eur_par_devise[devise_locale][2] is not None: # Taux moyen EUR/Devise
                        taux_moyen_eur_d = taux_annuels_eur_par_devise[devise_locale][2] 
                        montant_converti_eur = montant_local / taux_moyen_eur_d 
                        indemnites_mensuelles_pour_ce_pays_eur.append(montant_converti_eur)
                        # print(f"  Info: Pour {code_pays_ref}, mois {mois}, {montant_local} {devise_locale} converti en {montant_converti_eur:.2f} EUR (taux moyen {taux_moyen_eur_d:.6f} EUR/{devise_locale})")
                    # else: print(f"  Avert.: Pas de taux EUR ou de taux de change moyen pour {devise_locale} ({code_pays_ref}, mois {mois}).")
            if indemnites_mensuelles_pour_ce_pays_eur:
                moyenne_annuelle_pays = sum(indemnites_mensuelles_pour_ce_pays_eur) / len(indemnites_mensuelles_pour_ce_pays_eur)
                moyennes_annuelles_par_pays_ref_eur.append(moyenne_annuelle_pays)
                print(f"  Moyenne annuelle pour {code_pays_ref} (pays réf.): {moyenne_annuelle_pays:.2f} EUR")
            # else: print(f"  Avert.: Pas de données d'indemnité EUR pour calculer moyenne de {code_pays_ref}.")
        # else: print(f"  Avert.: Pays réf. {code_pays_ref} non trouvé ou sans barèmes pour calcul moyenne Europe.")
    if moyennes_annuelles_par_pays_ref_eur:
        moyenne_europe_finale = sum(moyennes_annuelles_par_pays_ref_eur) / len(moyennes_annuelles_par_pays_ref_eur)
        print(f"--- INDEMNITÉ MOYENNE EUROPÉENNE CALCULÉE POUR {annee_str}: {moyenne_europe_finale:.2f} EUR ---")
        return round(moyenne_europe_finale, 2)
    else:
        print(f"--- ERREUR: Impossible de calculer l'indemnité moyenne européenne pour {annee_str}. ---")
        return None 

def generer_csv_final(donnees_pays_complet, taux_annuels_eur_par_devise, annee_str, nom_fichier_sortie):
    print(f"\n--- Génération CSV: {nom_fichier_sortie} ---")
    lignes_csv = []
    entetes = [
        "Code Pays", "Nom Pays", "Date Validité Barème", "Montant Barème", "Devise Barème",
        "Taux (EUR par Devise) Début " + annee_str, 
        "Taux (EUR par Devise) Fin " + annee_str,
        "Taux (EUR par Devise) Moyen " + annee_str, 
        "Montant Barème (EUR)"
    ]
    lignes_csv.append(entetes)
    lignes_ecrites_count = 0

    for code_pays, data_pays in donnees_pays_complet.items():
        nom_pays = data_pays.get("n", "N/A")
        # barèmes_historiques_tries est déjà trié du plus récent au plus ancien par traiter_webmiss
        barèmes_historiques_tries = data_pays.get("a", []) 
        
        if not barèmes_historiques_tries:
            continue

        baremes_pertinents_pour_annee_csv = []
        
        # 1. Barèmes qui commencent DANS l'année annee_str
        for b in barèmes_historiques_tries:
            try:
                # S'assurer que b est bien une liste/tuple avec au moins une date
                if not (isinstance(b, (list, tuple)) and len(b) >= 1 and isinstance(b[0], str)):
                    continue
                b_date_obj = datetime.strptime(b[0], "%Y-%m-%d").date()
                if b_date_obj.year == int(annee_str):
                    baremes_pertinents_pour_annee_csv.append(b)
            except (ValueError, TypeError, IndexError):
                # print(f"Avertissement: Barème mal formé ignoré pour {code_pays} lors de la sélection annuelle: {b}")
                continue
        
        # 2. Le barème le plus récent strictement ANTÉRIEUR au 1er janvier de annee_str
        bareme_applicable_debut_annee = None
        for b in barèmes_historiques_tries: # Toujours trié du plus récent au plus ancien
            try:
                if not (isinstance(b, (list, tuple)) and len(b) >= 1 and isinstance(b[0], str)):
                    continue
                # On cherche le premier barème (donc le plus récent) AVANT le début de annee_str
                if b[0] < f"{annee_str}-01-01":
                    bareme_applicable_debut_annee = b
                    break 
            except TypeError: # Au cas où b[0] ne serait pas une chaîne comparable
                continue
        
        # 3. Ajouter ce barème de début d'année s'il existe et n'est pas déjà couvert
        if bareme_applicable_debut_annee:
            # L'ajouter seulement s'il n'y a pas déjà un barème dans l'année qui commence le 01/01
            # ou si la liste des barèmes de l'année est vide (celui d'avant s'applique donc)
            ajouter_bareme_avant = True
            if not baremes_pertinents_pour_annee_csv: # Si aucun barème ne commence cette année-là
                 baremes_pertinents_pour_annee_csv.append(bareme_applicable_debut_annee)
                 ajouter_bareme_avant = False # Déjà ajouté
            else:
                for b_annuel in baremes_pertinents_pour_annee_csv:
                    if b_annuel[0] == f"{annee_str}-01-01": # Un barème de l'année commence déjà le 01/01
                        ajouter_bareme_avant = False
                        break
            if ajouter_bareme_avant: # Si aucun barème de l'année ne commence le 01/01
                baremes_pertinents_pour_annee_csv.append(bareme_applicable_debut_annee)
        
        # S'il n'y a absolument aucun barème trouvé (ni de l'année, ni d'avant),
        # et qu'il y avait des barèmes historiques, on prend le plus récent de tous comme fallback.
        # (C'est un cas de dernier recours, la logique ci-dessus devrait en trouver un s'il existe)
        if not baremes_pertinents_pour_annee_csv and barèmes_historiques_tries:
             if barèmes_historiques_tries[0] and isinstance(barèmes_historiques_tries[0], (list, tuple)) and len(barèmes_historiques_tries[0]) == 3: 
                baremes_pertinents_pour_annee_csv.append(barèmes_historiques_tries[0])

        # Dédoublonnage final et tri chronologique pour l'écriture dans le CSV
        baremes_final_pour_csv = [] 
        vus_pour_csv = set()
        # Tri par date (plus récente) puis par montant (plus élevé) pour le dédoublonnage par date/devise
        # Ce tri est fait pour que si plusieurs barèmes ont la même date de début et même devise, on garde le plus avantageux
        baremes_pertinents_pour_annee_csv.sort(key=lambda x: (x[0] if x and x[0] else "", -float(x[2] if x and len(x) == 3 and x[2] is not None else 0)))
        
        for b_unique in baremes_pertinents_pour_annee_csv:
            if isinstance(b_unique, (list, tuple)) and len(b_unique) == 3:
                # Dédoublonnage basé sur la date de validité et la devise pour le CSV final
                identifiant_b_unique = (str(b_unique[0]), str(b_unique[1])) 
                if identifiant_b_unique not in vus_pour_csv:
                    baremes_final_pour_csv.append(b_unique)
                    vus_pour_csv.add(identifiant_b_unique)
            # else: print(f"  Avertissement: Barème malformé ignoré pour CSV (pays {code_pays}): {b_unique}")

        baremes_final_pour_csv.sort(key=lambda x: x[0]) # Tri chronologique final pour l'affichage
        
        for bareme_a_ecrire in baremes_final_pour_csv:
            # ... (le reste de la logique d'écriture de la ligne CSV reste la même)
            if not (isinstance(bareme_a_ecrire, (list, tuple)) and len(bareme_a_ecrire) == 3): continue
            date_validite, devise_indemnite, montant_indemnite = bareme_a_ecrire
            taux_pour_devise_eur_d = taux_annuels_eur_par_devise.get(devise_indemnite, [None,None,None])
            taux_debut_eur_d, taux_fin_eur_d, taux_moyen_eur_d = taux_pour_devise_eur_d
            montant_eur = None
            if montant_indemnite is not None and taux_moyen_eur_d is not None:
                try: montant_eur = round(float(montant_indemnite) / taux_moyen_eur_d, 2) 
                except (ValueError, TypeError): montant_eur = "Erreur Calc."
            ligne = [code_pays, nom_pays, date_validite, montant_indemnite if montant_indemnite is not None else "N/A", 
                devise_indemnite, 
                f"{taux_debut_eur_d:.6f}" if taux_debut_eur_d is not None else "N/A",
                f"{taux_fin_eur_d:.6f}" if taux_fin_eur_d is not None else "N/A",
                f"{taux_moyen_eur_d:.6f}" if taux_moyen_eur_d is not None else "N/A",
                montant_eur if montant_eur is not None else "N/A"]; 
            lignes_csv.append(ligne); lignes_ecrites_count +=1
    try:
        # ... (logique d'écriture du fichier CSV) ...
        nom_fichier_sortie_complet = nom_fichier_sortie 
        dossier_parent = os.path.dirname(nom_fichier_sortie_complet)
        if dossier_parent and not os.path.exists(dossier_parent) and dossier_parent != ".": # Ne pas essayer de créer si dossier_parent est vide (cas racine)
            os.makedirs(dossier_parent, exist_ok=True)
        with open(nom_fichier_sortie_complet, 'w', newline='', encoding='utf-8-sig') as f_csv: 
            writer = csv.writer(f_csv, delimiter=';'); writer.writerows(lignes_csv)
        print(f"--- Fichier CSV '{nom_fichier_sortie_complet}' généré ({lignes_ecrites_count} lignes). Emplacement: {os.path.abspath(nom_fichier_sortie_complet)} ---")
    except IOError as e: print(f"ERREUR écriture CSV '{nom_fichier_sortie_complet}': {e}")
    except Exception as ex_csv: print(f"ERREUR INATTENDUE CSV: {ex_csv}"); import traceback; print(traceback.format_exc())

# ---
if __name__ == "__main__":
    print("Automatisation DGFiP"); print("===================\n")
    annee_actuelle_dt = datetime.now()
    annees_a_traiter = [str(annee_actuelle_dt.year - 1), str(annee_actuelle_dt.year)] 
    # annees_a_traiter = ["2024"] 

    for annee_en_cours in annees_a_traiter:
        print(f"\n\n************************************************************")
        print(f"*** DÉBUT DU TRAITEMENT POUR L'ANNÉE : {annee_en_cours} ***")
        print(f"************************************************************\n")
        
        if annee_en_cours not in INDEMNITES_MANUELLES_SPECIFIQUES:
            INDEMNITES_MANUELLES_SPECIFIQUES[annee_en_cours] = {}
        indemnites_manuelles_pour_annee_courante = INDEMNITES_MANUELLES_SPECIFIQUES[annee_en_cours]

        donnees_pays = {k: v.copy() for k, v in PAYS_INITIAUX_ET_CORRECTIONS.items()}
        for code_p in donnees_pays:
            if "a" not in donnees_pays[code_p]: donnees_pays[code_p]["a"] = []

        contenu_webpays_txt = telecharger_fichier_dgfip(WEBPAYS_URL)
        if contenu_webpays_txt: donnees_pays = traiter_webpays(contenu_webpays_txt, donnees_pays)
        else: print("Échec téléchargement Webpays.")

        if donnees_pays: 
            contenu_webmiss_txt = telecharger_fichier_dgfip(WEBMISS_URL)
            donnees_pays = traiter_webmiss(contenu_webmiss_txt, donnees_pays, annee_en_cours, indemnites_manuelles_pour_annee_courante)
        else: print("Traitement Webmiss ignoré.")

        contenu_webtaux_txt = telecharger_fichier_dgfip(WEBTAUX_URL)
        donnees_taux_historique_eur_par_devise = {} # Contiendra des taux EUR/Devise
        if contenu_webtaux_txt: donnees_taux_historique_eur_par_devise = traiter_webtaux(contenu_webtaux_txt, annee_en_cours)
        else: print("Échec téléchargement Webtaux.")
        
        taux_annuels_eur_par_devise = {} # Stockera des taux EUR/Devise
        if donnees_taux_historique_eur_par_devise:
            taux_annuels_eur_par_devise = calculer_taux_annuels(donnees_taux_historique_eur_par_devise, annee_en_cours)
        else: print("Aucune donnée de taux historique pour calculer les taux annuels.")

        forfait_europe_valeur_calculee = None
        if donnees_pays and taux_annuels_eur_par_devise: 
            forfait_europe_valeur_calculee = calculer_moyenne_indemnites_europe(donnees_pays, annee_en_cours, PAYS_EUROPE_POUR_MOYENNE, taux_annuels_eur_par_devise) # Passe les taux EUR/Devise
            if forfait_europe_valeur_calculee is not None:
                print(f"Application du forfait Europe calculé ({forfait_europe_valeur_calculee} EUR) aux pays cibles pour {annee_en_cours}...")
                date_application_forfait = f"{annee_en_cours}-01-01" 
                for code_pays_cible in PAYS_CIBLES_FORFAIT_MOYEN_EU:
                    if code_pays_cible not in donnees_pays:
                        donnees_pays[code_pays_cible] = {"n": PAYS_INITIAUX_ET_CORRECTIONS.get(code_pays_cible, {}).get("n", code_pays_cible), "a": []}
                    print(f"  Application du forfait Europe à {code_pays_cible} ({donnees_pays[code_pays_cible].get('n', code_pays_cible)})")
                    donnees_pays[code_pays_cible]["a"] = [[date_application_forfait, "EUR", forfait_europe_valeur_calculee]]
            else: print(f"Forfait Europe non calculé pour {annee_en_cours}.")
        
        if donnees_pays and taux_annuels_eur_par_devise: 
            nom_base_csv = f"dgfip_indemnites_{annee_en_cours}.csv"
            dossier_cible = "impot_calc"
            nom_csv_final = os.path.join(dossier_cible, nom_base_csv)
            if not os.path.exists(dossier_cible) and dossier_cible != ".":
                try: os.makedirs(dossier_cible, exist_ok=True)
                except OSError as e:
                    print(f"Avert.: Impossible de créer dossier {dossier_cible}: {e}. CSV écrit localement.")
                    dossier_cible = "." ; nom_csv_final = os.path.join(dossier_cible, nom_base_csv)
            generer_csv_final(donnees_pays, taux_annuels_eur_par_devise, annee_en_cours, nom_csv_final)
        else: print(f"\nImpossible de générer le CSV final pour {annee_en_cours}.")

        if forfait_europe_valeur_calculee is not None:
            print(f"\nVALEUR FINALE DU FORFAIT EUROPE MOYEN CALCULÉ POUR {annee_en_cours}: {forfait_europe_valeur_calculee:.2f} EUR")
        else: print(f"\nAucun forfait Europe moyen n'a pu être calculé pour {annee_en_cours}.")
        print(f"*** FIN DU TRAITEMENT POUR L'ANNÉE : {annee_en_cours} ***")
    print("\nFin du script DGFiP.")
