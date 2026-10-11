"""Lot Ouvert : guides pratiques. Contenu vérifié en octobre 2026 sur entreprendre.service-public.gouv.fr et marche-public.fr.
Les montants (seuils) changent régulièrement : ils sont regroupés ici pour être mis à jour au même endroit."""

VERIFIE = "octobre 2026"
SRC_CANDIDATURE = ("Service-public.fr, préparer le dossier de candidature", "https://entreprendre.service-public.gouv.fr/vosdroits/F32144")
SRC_OFFRE = ("Service-public.fr, préparer l'offre", "https://entreprendre.service-public.gouv.fr/vosdroits/F32154")
SRC_SEUILS = ("Marche-public.fr, seuils 2026", "https://www.marche-public.fr/Marches-publics/Definitions/Entrees/Seuil.htm")

GUIDES = [
 {"slug": "repondre-a-un-appel-d-offres", "titre": "Répondre à un appel d'offres public pour la première fois",
  "resume": "Les sept étapes, de l'annonce au dépôt, expliquées sans jargon.",
  "sources": [SRC_CANDIDATURE, SRC_OFFRE],
  "corps": """
<p class="intro">Une mairie, un collège ou un hôpital qui a besoin de travaux, d'un service ou de fournitures doit le faire savoir, et toute entreprise peut proposer ses services. Voici le chemin complet, dans l'ordre.</p>
<h2>1. Trouver une annonce qui vous correspond</h2>
<p>Cherchez par métier et par département. Sur ce site, chaque annonce indique la date limite, le type de marché et, quand l'acheteur l'a publié, le montant estimé et le nombre de lots. <a href="../../metiers/">Voir les métiers</a></p>
<h2>2. Télécharger le dossier</h2>
<p>Tout ce qu'il faut savoir est dans les documents de la consultation, à télécharger sur la plateforme de l'acheteur. Les deux plus importants sont le règlement de consultation, qui fixe les règles du jeu (pièces à fournir, critères de notation, date limite), et le cahier des charges, qui décrit le travail attendu.</p>
<h2>3. Décider si vous y allez</h2>
<p>Un dossier demande souvent plusieurs jours de travail. Avant de vous lancer, regardez qui détient le marché aujourd'hui, combien d'entreprises répondent d'habitude chez cet acheteur et ce que pèse le prix dans la note. <a href="../faut-il-repondre/">Comment décider</a></p>
<h2>4. Préparer la candidature</h2>
<p>La candidature présente votre entreprise et prouve qu'elle a le droit et les moyens de faire le travail. Elle se remplit soit avec un formulaire européen unique, le DUME, soit avec deux formulaires français, le DC1 et le DC2. <a href="../documents-a-fournir/">Le détail des documents</a></p>
<h2>5. Préparer l'offre</h2>
<p>L'offre comprend deux parties : l'offre technique, appelée mémoire technique, qui explique comment vous allez faire le travail, et l'offre financière, c'est-à-dire vos prix. L'acheteur peut demander d'autres pièces, par exemple un planning. <a href="../memoire-technique/">Rédiger le mémoire technique</a></p>
<h2>6. Déposer avant la date et l'heure limites</h2>
<p>À partir de 60 000 €, la candidature et l'offre se déposent en ligne, sur la plateforme de l'acheteur. En dessous, un envoi par e-mail peut être accepté. N'attendez pas la dernière heure : un dépôt arrivé après l'heure limite n'est pas examiné.</p>
<h2>7. Attendre le résultat</h2>
<p>L'acheteur note les offres selon les critères annoncés. Si vous êtes retenu, vous signez l'acte d'engagement, qui est le contrat du marché. Sinon, vous pouvez demander les raisons du rejet : c'est utile pour la fois suivante.</p>
<h2>Les trois erreurs qui éliminent un dossier</h2>
<ul><li>Oublier un document demandé : l'offre devient irrégulière.</li><li>Ne pas suivre la présentation imposée par le règlement de consultation (nombre de pages, cadre de réponse).</li><li>Proposer un prix sans rapport avec le travail demandé : l'acheteur doit écarter les offres anormalement basses.</li></ul>"""},

 {"slug": "documents-a-fournir", "titre": "Les documents à fournir pour un marché public",
  "resume": "Candidature et offre : ce que chaque pièce contient et ce qui est vraiment obligatoire.",
  "sources": [SRC_CANDIDATURE, SRC_OFFRE],
  "corps": """
<p class="intro">Un dossier de réponse a toujours deux parties : la candidature, qui parle de votre entreprise, et l'offre, qui parle de ce marché précis.</p>
<h2>La candidature</h2>
<dl class="definitions">
<div><dt>DUME</dt><dd>Document unique de marché européen. Un seul formulaire en ligne qui remplace les autres. L'acheteur ne peut jamais refuser une candidature présentée sous cette forme. Rempli en ligne, il vous évite de fournir l'attestation de régularité fiscale et l'attestation de vigilance.</dd></div>
<div><dt>DC1 et DC2</dt><dd>Les deux formulaires français. Le DC1 est la lettre de candidature, avec la déclaration sur l'honneur. Le DC2 décrit votre entreprise : identité, chiffre d'affaires des trois dernières années, moyens et références.</dd></div>
<div><dt>Déclaration sur l'honneur</dt><dd>Vous attestez qu'aucune interdiction de répondre aux marchés publics ne vous concerne. Elle est incluse dans le DUME et dans le DC1.</dd></div>
<div><dt>DC4</dt><dd>À fournir seulement si vous faites appel à un sous-traitant, un par sous-traitant.</dd></div>
</dl>
<h2>Ce que l'acheteur peut exiger</h2>
<ul><li>Un chiffre d'affaires annuel minimum. Il ne peut pas dépasser une fois et demie le montant estimé du marché.</li><li>Des références de travaux ou de prestations comparables.</li><li>Pour les travaux, votre assurance de responsabilité décennale.</li></ul>
<p>Si vous débutez et n'avez pas trois ans de chiffre d'affaires, indiquez-le : une entreprise récente peut prouver ses capacités autrement, par exemple par l'expérience de son dirigeant.</p>
<h2>L'offre</h2>
<dl class="definitions">
<div><dt>Mémoire technique</dt><dd>Votre réponse au cahier des charges : méthode, équipe, matériel, planning, engagements. C'est lui qui est noté sur les critères autres que le prix.</dd></div>
<div><dt>Bordereau des prix unitaires</dt><dd>Pour les marchés payés à l'unité : un prix pour chaque prestation de la liste fournie par l'acheteur.</dd></div>
<div><dt>Décomposition du prix global et forfaitaire</dt><dd>Pour les marchés à prix forfaitaire : le détail de votre prix total. Vous vous engagez sur ce forfait, quelles que soient les quantités réelles.</dd></div>
<div><dt>Acte d'engagement</dt><dd>Le contrat. Il est complété et signé par l'entreprise retenue, au moment de l'attribution.</dd></div>
</dl>
<h2>Faut-il signer ?</h2>
<p>La réglementation n'impose de signer ni le DUME, ni le DC1, ni le DC2. L'acheteur peut toutefois le demander dans le règlement de consultation : vérifiez toujours ce point.</p>"""},

 {"slug": "memoire-technique", "titre": "Le mémoire technique : à quoi il sert et comment l'écrire",
  "resume": "La pièce qui fait la différence quand le prix ne décide pas tout.",
  "sources": [SRC_OFFRE],
  "corps": """
<p class="intro">Le mémoire technique explique à l'acheteur comment vous allez réaliser le marché. C'est lui qui est noté sur tous les critères autres que le prix, et ces critères pèsent souvent plus de la moitié de la note.</p>
<h2>Ce qu'il contient</h2>
<p>Il répond point par point au cahier des charges : présentation de l'entreprise, méthode de travail, équipe et matériel affectés, planning, et le cas échéant vos engagements sur l'environnement ou l'insertion. Il n'existe pas de modèle officiel, sauf si l'acheteur impose le sien.</p>
<h2>Commencez par le règlement de consultation</h2>
<p>Il fixe les règles : critères et sous-critères avec leurs points, parfois un nombre maximal de pages, une présentation en tableau ou l'interdiction des annexes. Un mémoire qui ignore ces règles perd des points, voire est écarté.</p>
<h2>Construisez le plan sur la grille de notation</h2>
<ul><li>Une partie par sous-critère, dans le même ordre et avec le même intitulé que dans le règlement.</li><li>Une longueur proportionnelle aux points : inutile d'écrire trois pages sur un sous-critère qui en vaut cinq sur cent.</li><li>Des faits plutôt que des adjectifs : qui intervient, avec quel matériel, en combien de jours.</li></ul>
<h2>Répondez à ce chantier, pas à tous les chantiers</h2>
<p>L'acheteur lit des dizaines de mémoires identiques d'un marché à l'autre. Citez les contraintes propres à celui-ci : site occupé, horaires imposés, accès difficile, délai serré. Montrez que vous avez lu le cahier des charges.</p>
<h2>N'écrivez que ce qui est vrai</h2>
<p>Le mémoire vous engage. Une référence, un effectif ou une qualification inexacts peuvent vous coûter le marché, et vous exposer davantage s'ils sont découverts après la signature.</p>
<h2>Relisez comme un correcteur</h2>
<p>Reprenez la grille de notation et vérifiez que chaque sous-critère trouve sa réponse en moins de dix secondes de lecture. Sur ce site, la fiche de chaque annonce affiche les critères et leur poids quand l'acheteur les a publiés.</p>"""},

 {"slug": "lire-une-annonce", "titre": "Lire une annonce de marché public sans se perdre",
  "resume": "Procédure adaptée, lots, critères, visite : le vocabulaire qui revient dans chaque avis.",
  "sources": [SRC_SEUILS, SRC_OFFRE],
  "corps": """
<p class="intro">Une annonce de marché public utilise toujours les mêmes mots. Une fois compris, vous lisez un avis en deux minutes.</p>
<dl class="definitions">
<div><dt>Acheteur</dt><dd>L'organisme public qui passe le marché : commune, département, hôpital, office HLM, établissement scolaire.</dd></div>
<div><dt>Procédure adaptée</dt><dd>La procédure des marchés de taille modeste. L'acheteur fixe librement ses règles et peut négocier avec les candidats. C'est la porte d'entrée habituelle des petites entreprises.</dd></div>
<div><dt>Procédure formalisée, ou appel d'offres ouvert</dt><dd>La procédure des gros marchés, aux règles strictes et sans négociation. En 2026 et 2027, elle s'applique à partir de 140 000 € HT pour les fournitures et services de l'État, 216 000 € HT pour ceux des collectivités, et 5 404 000 € HT pour les travaux.</dd></div>
<div><dt>Lots</dt><dd>Le marché est découpé en parties attribuées séparément, par exemple gros œuvre, électricité, peinture. Vous pouvez répondre à un seul lot.</dd></div>
<div><dt>Critères d'attribution</dt><dd>La grille de notation, avec le poids de chaque critère. Un prix à 40 % signifie que 60 % de la note se joue sur votre dossier écrit.</dd></div>
<div><dt>Visite obligatoire</dt><dd>Vous devez vous rendre sur place avant de répondre, souvent à une date imposée. Sans l'attestation de visite, l'offre est rejetée.</dd></div>
<div><dt>Variantes</dt><dd>Une solution différente de celle décrite par l'acheteur, par exemple un autre matériau. Elles sont en principe autorisées, sauf si l'annonce les interdit.</dd></div>
<div><dt>Accord-cadre</dt><dd>Un contrat qui fixe les conditions pour plusieurs années, les commandes arrivant ensuite au fur et à mesure des besoins.</dd></div>
<div><dt>Délai de validité des offres</dt><dd>La durée pendant laquelle votre prix vous engage. En pratique, 90 à 120 jours.</dd></div>
</dl>
<h2>Pourquoi vous ne voyez pas tous les marchés</h2>
<p>La publication dans un bulletin officiel ou un journal d'annonces légales n'est obligatoire qu'à partir de 90 000 € HT. En dessous, l'acheteur choisit librement sa publicité. Et il peut se passer de publicité et de mise en concurrence sous 60 000 € HT pour les fournitures et services, et sous 100 000 € HT pour les travaux. Beaucoup de petits marchés se gagnent donc en étant déjà connu de l'acheteur.</p>"""},

 {"slug": "faut-il-repondre", "titre": "Faut-il répondre à ce marché ? Trois questions avant de se lancer",
  "resume": "Répondre coûte des jours de travail. Comment repérer les dossiers qui valent le coup.",
  "sources": [SRC_OFFRE],
  "corps": """
<p class="intro">Répondre à tout est la meilleure façon de s'épuiser. Les entreprises qui gagnent régulièrement choisissent leurs dossiers. Trois questions suffisent pour trier.</p>
<h2>Combien serons-nous à répondre ?</h2>
<p>Certains acheteurs reçoivent deux offres par marché, d'autres quinze. Sur chaque fiche d'annonce, la lecture rapide indique le nombre d'offres reçues habituellement par cet acheteur, d'après ses résultats publiés. Deux ou trois offres, vos chances sont réelles. Dix ou plus, il faut un avantage net.</p>
<h2>Qui détient le marché aujourd'hui ?</h2>
<p>Si la même entreprise a remporté les trois derniers marchés comparables, l'acheteur en est probablement satisfait. Ce n'est pas perdu d'avance, mais il faudra être nettement meilleur ou moins cher. À l'inverse, un acheteur qui change souvent de titulaire est ouvert aux nouveaux venus.</p>
<h2>Sur quoi serai-je jugé ?</h2>
<p>Regardez le poids du prix. S'il compte pour 70 %, le moins cher l'emporte presque toujours : n'y allez que si vos prix sont bien placés. S'il compte pour 40 %, un bon mémoire technique peut battre un concurrent moins cher.</p>
<h2>Les signaux qui doivent vous faire renoncer</h2>
<ul><li>Une visite obligatoire à une date où vous ne pouvez pas vous déplacer.</li><li>Un chiffre d'affaires minimum que vous n'atteignez pas.</li><li>Une date limite trop proche pour rédiger un dossier sérieux.</li><li>Un chantier trop gros pour votre équipe : gagner un marché qu'on ne peut pas tenir coûte plus cher que de le perdre.</li></ul>
<p>Ces repères décrivent le passé d'un acheteur. Ils aident à décider, ils ne prédisent pas le résultat.</p>"""},

 {"slug": "marches-bientot-relances", "titre": "Marchés bientôt relancés : comment se préparer avant l'annonce",
  "resume": "Un marché qui se termine est souvent remis en concurrence. Ce que vous pouvez faire des mois à l'avance.",
  "sources": [SRC_SEUILS],
  "corps": """
<p class="intro">Un marché d'entretien, de nettoyage ou de fourniture a une durée. Quand elle se termine, l'acheteur doit le plus souvent remettre le marché en concurrence. Savoir quand donne plusieurs mois d'avance sur ceux qui découvrent l'annonce le jour de sa parution.</p>
<h2>D'où viennent ces dates</h2>
<p>Quand un marché est attribué, l'acheteur publie un résultat qui indique souvent la durée du contrat ou sa date de fin. Ce site calcule la fin prévue à partir de ces informations. <a href="../../relances/">Voir les marchés qui arrivent à échéance</a></p>
<h2>Ce que ces dates ne disent pas</h2>
<ul><li>Un marché peut être reconduit sans nouvelle annonce si le contrat le prévoit.</li><li>La durée publiée couvre parfois déjà les reconductions possibles.</li><li>L'acheteur peut décider de ne pas renouveler, ou de regrouper plusieurs marchés.</li></ul>
<p>Prenez la date comme un repère, et vérifiez auprès de l'acheteur.</p>
<h2>Ce que vous pouvez faire à l'avance</h2>
<ul><li>Repérer l'entreprise en place et ses autres marchés, pour savoir à qui vous aurez affaire.</li><li>Rassembler vos références comparables et les attestations de vos clients.</li><li>Préparer la trame de votre mémoire technique, à adapter le jour venu.</li><li>Créer une alerte sur ce métier et ce département pour ne pas manquer l'annonce.</li></ul>
<h2>Se faire connaître de l'acheteur</h2>
<p>Avant de lancer une consultation, un acheteur a le droit d'échanger avec des entreprises pour connaître ce que le marché propose. Vous pouvez vous présenter, demander quand le marché sera relancé et sous quelle forme. En revanche, une fois la consultation publiée, toute question passe par la plateforme et la réponse est donnée à tous les candidats.</p>
<h2>Les petits marchés se gagnent ainsi</h2>
<p>Sous 60 000 € HT pour les fournitures et services, et sous 100 000 € HT pour les travaux, l'acheteur peut choisir une entreprise sans publicité. Il s'adresse alors à celles qu'il connaît. Être identifié avant compte autant que bien répondre après.</p>"""},
]
