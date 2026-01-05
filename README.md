# SOC-Lab

![Bannière](images/Monimage1.png)

> **Résumé :** Un laboratoire de détection complet simulant les techniques MITRE ATT&CK (T1547) et concevant des règles de détection à l'aide de Splunk Enterprise et Sysmon.

## Architecture
| Composant | Technologie | Rôle |
|-----------|------------|------|
| **SIEM** | Splunk Enterprise | Agrégation et analyse des journaux |
| **Endpoint** | Windows 11 | Machine de la Victime |
| **Télémétrie** | Sysmon (SwiftOnSecurity) | Journalisation avancée |
| **Transport** | Universal Forwarder | Expédition des journaux |

> [!WARNING]
> Dans cette architecture, la machine physique joue le rôle de la machine de la victime. **Cela ne doit jamais être le choix privilégié dans une situation normale.** Dans mon cas, pour des soucis de compatibilité, j'ai toutefois été contraint d'utiliser la machine physique comme machine victime.

---
**Schéma de flux :**
[Windows 11 + Sysmon + UF] ---(Port 9997)---> [Windows Server 2022 + Splunk Enterprise]

### 📚 Prérequis : Installation de l'Infrastructure
Avant de configurer la collecte, Splunk Enterprise et l'Universal Forwarder doivent être installés. Voici les tutoriels que j'ai personnellement utilisés:

1.  **[Installation de Splunk Enterprise sur Windows](https://www.youtube.com/watch?v=kESCizBHhtM)** (Serveur)
2.  **[Installation de l'Universal Forwarder sur Windows](https://www.youtube.com/watch?v=wd4BLsJThQY)** (Victime)

> *Note : Les interfaces peuvent varier légèrement selon les versions, mais le principe reste identique.*

**⚠️ Modifications OBLIGATOIRES pour ce Lab :**

Lors de l'installation de l'Universal Forwarder sur la machine victime :

1. **Receiving Indexer (Indexeur de réception) :**
   - **IP :** Entrez l'adresse IP de votre Serveur Splunk Enterprise (Destination).
   - **Port :** `9997` (Port par défaut).

2. **Compte de service :**
   - Sélectionnez **Local System** pour garantir que l'agent ait les droits suffisants pour lire les journaux de Sécurité et Système.

3. **Logs par défaut :**
   - **Décochez tout** dans l'installateur (Application, Security, System).
   - *Nous allons configurer cela manuellement et plus proprement via le fichier `inputs.conf` à l'Étape 2.*

---
## Installation et Configuration

### Étape 1 : Déploiement de Sysmon (Endpoint)
Sysmon a été installé sur la machine Windows 11 avec la configuration communautaire de référence (SwiftOnSecurity) pour maximiser la visibilité sur les activités critiques.

> [!IMPORTANT]
> N'oubliez pas de télécharger le fichier [sysmonconfig-export.xml](https://github.com/SwiftOnSecurity/sysmon-config/blob/master/sysmonconfig-export.xml).


```powershell
# Téléchargement de Sysmon et de la config sysmonconfig-export.xml
Invoke-WebRequest -Uri https://download.sysinternals.com/files/Sysmon.zip -OutFile Sysmon.zip
Expand-Archive Sysmon.zip -DestinationPath C:\Sysmon

# Installation avec configuration SwiftOnSecurity
cd C:\Sysmon
# Veuillez remplacer <chemin_config> par le chemin réel du fichier téléchargé
.\Sysmon64.exe -i <chemin_config>\sysmonconfig-export.xml -accepteula
```

**Processus de validation**:

![Sysmon installé](images/sysmoninstallé1.png)

> *Installation réussie de Sysmon. Le service est actif et les logs sont visibles dans l'Observateur d'événements Windows sous `Microsoft-Windows-Sysmon/Operational`.*

**Sysmon a bien été installé et est fonctionnel !**

### Étape 2 : Configuration de l'Universal Forwarder

L'Universal Forwarder (UF) a été configuré pour capturer les logs Sysmon et les transmettre au serveur Splunk via TCP/9997.

**Fichier :**  `C:\Program Files\SplunkUniversalForwarder\etc\system\local\inputs.conf` (À créer s'il n'existe pas). Voici un template dont vous pourrez vous servir:
**[Télécharger le template complet ici](config/Template_inputs.conf)**
 
### Étape 3 : Configuration des Index sur Splunk Enterprise

Sur le serveur Windows Server 2022, Splunk doit être configuré pour accepter les connexions entrantes des Forwarders.

Vous pouvez configurer de votre côté la réception via l'interface web de Splunk Enterprise :
Paramètres > Transfert et réception > Configurer la réception

Ajout du port 9997 pour correspondre aux instructions ci-dessus:

![Port de réception 9997 ouvert](images/portouvert.png)

Maintenant que l'ouverture logicielle est effectuée, on peut passer à l'ouverture du réseau toujours sur le serveur Windows Server 2022: 

```powershell
New-NetFirewallRule -DisplayName "Splunk Receiver" -Direction Inbound -Protocol TCP -LocalPort 9997 -Action Allow
```


Une fois la règle pare-feu activée sur le serveur, validez immédiatement que le flux est ouvert depuis la machine **Victime** :
```powershell
 Test-NetConnection -ComputerName ADRESSEDEVOTRESERVEUR -Port 9997
```

**Résultat attendu :** `TcpTestSucceeded : True`.
*Si ce test échoue, inutile d'aller plus loin : vérifiez l'IP et le Pare-feu.*

>[!NOTE]
> Avant de recevoir les logs, les index définis dans la configuration de l'UF doivent être créés sur le serveur Splunk.**Sans cela, Splunk rejettera les données entrantes.**

Pour créer des indexes, il vous faut aller sur Splunk Enterprise puis aller dans Paramètres > Données > Index > Nouveau index. Vous pouvez tout laisser par défaut.

**Index à créer :**
- `sysmon`
- `windows_security`
- `windows_system`
- `windows_app`
  
**Attention, ces indexes sont les mêmes que ceux indiqués dans votre fichier de configuration inputs.conf**
  
![Indexes](images/Indexes_créés.png)



>[!NOTE]
> A ce stade, "index=sysmon" devrait vous retourner un résultat non vide sur Splunk Entreprise après quelques minutes. Si ce n'est pas le cas, vérifiez les logs de splunkd dans le répertoire par défaut est **"C:\Program Files\SplunkUniversalForwarder\var\log\splunk\splunkd.log"** sur la machine avec l'Universal Forwarder pour débugguer. Dans mon cas, le **code d'erreur associé était le 5**, indiquant un manque de permission. La commande **C:\Windows\System32>wevtutil sl Microsoft-Windows-Sysmon/Operational /ca:O:BAG:SYD:(A;;0xf0007;;;SY)(A;;0x7;;;BA)(A;;0x7;;;SO)(A;;0x7;;;IU)(A;;0x7;;;SU)(A;;0x7;;;S-1-5-3-1024-1065365936-1281604716-3511738428-1654721687-9514)** sur l'invite de commande en mode administrateur m'a donc permis d'y remédier. **N'oubliez pas de redémarrer le service SplunkForwarder!**
>![Résultat non vide](images/Vérif_Sysmon_Splunk.png)

---
## Simulation d'Attaque et Détection (MITRE T1547)

>[!IMPORTANT]
> Le choix de la technique d'attaque n'est pas anodin pour mon premier Lab SOC. 
> J'ai choisi la technique [T1547.001 (Registry Run Keys)](https://attack.mitre.org/techniques/T1547/001/) car elle représente **un mécanisme de persistance fondamental** utilisé par une majorité de **malwares (APT, Ransomwares) pour survivre aux redémarrages**. De plus, elle permet de démontrer **la supériorité de la télémétrie Sysmon (Event ID 11 & 13) par rapport aux journaux Windows standards** pour l'attribution de l'action.

