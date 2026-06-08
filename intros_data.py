# -*- coding: utf-8 -*-
"""
Intro narrativi per macro-aree e argomenti — Apple WWDC 2026.
Scritti in forma forward-looking (validi anche prima del keynote): non citano
annunci specifici, inquadrano il tema. La revisione finale (fase 2) puo
riscriverli alla luce di cio che e stato effettivamente annunciato.

Schema per voce: h2It / h2En (sottotitolo breve) + bodyIt / bodyEn (paragrafo).
Le chiavi corrispondono agli slug in data/news.json.
"""

MACRO_AREA_INTROS = {
    "sistemi-operativi": {
        "h2It": "Le nuove versioni di iOS, iPadOS e macOS",
        "h2En": "The new iOS, iPadOS and macOS releases",
        "bodyIt": "È l'area che riguarda tutti: le funzioni di sistema che arriveranno sui dispositivi nei prossimi mesi. Sotto questo cappello trovi le novità delle piattaforme — iOS, iPadOS, macOS, watchOS, tvOS — lette dal punto di vista di chi le userà ogni giorno, non da quello della demo sul palco. Cosa cambia davvero nel modo di usare iPhone, iPad e Mac, e cosa è soltanto rifinitura.",
        "bodyEn": "This is the area that touches everyone: the system features landing on devices in the coming months. Under this heading you find the platform news — iOS, iPadOS, macOS, watchOS, tvOS — read from the point of view of those who'll use them daily, not from the stage demo. What really changes in how you use iPhone, iPad and Mac, and what is merely polish.",
    },
    "apple-intelligence": {
        "h2It": "Apple Intelligence e il nuovo corso di Siri",
        "h2En": "Apple Intelligence and the new Siri",
        "bodyIt": "Il fronte più osservato dell'evento. Qui si gioca la credibilità di Apple sull'AI: quanto è reale il nuovo Siri, quali funzioni arrivano davvero e quando, cosa gira sul dispositivo e cosa nel cloud. Raccolgo qui gli annunci di Apple Intelligence con un occhio critico alla distanza tra promessa e disponibilità effettiva.",
        "bodyEn": "The most-watched front of the event. This is where Apple's AI credibility is decided: how real the new Siri is, which features actually ship and when, what runs on-device and what in the cloud. I gather the Apple Intelligence announcements here with a critical eye on the gap between promise and actual availability.",
    },
    "sviluppatori": {
        "h2It": "Xcode, Swift e gli strumenti per chi costruisce",
        "h2En": "Xcode, Swift and the tools for those who build",
        "bodyIt": "Il WWDC nasce come conferenza per sviluppatori, e questa è l'area che ne raccoglie l'anima tecnica: novità di Swift, Xcode, dei framework e degli SDK, delle API che apriranno nuove possibilità alle app. Meno spettacolo, più sostanza: le decisioni che orienteranno il lavoro di centinaia di migliaia di sviluppatori.",
        "bodyEn": "WWDC was born as a developer conference, and this is the area that gathers its technical soul: news on Swift, Xcode, frameworks and SDKs, the APIs that open new possibilities for apps. Less spectacle, more substance: the decisions that will steer the work of hundreds of thousands of developers.",
    },
    "design-interfacce": {
        "h2It": "Il linguaggio visivo e le interfacce",
        "h2En": "The visual language and interfaces",
        "bodyIt": "Come cambiano l'aspetto e il comportamento delle interfacce Apple: nuovi linguaggi di design, gesti, modi di navigare. È l'area in cui le scelte estetiche diventano scelte di prodotto, perché un cambio di interfaccia ridisegna le abitudini di milioni di persone.",
        "bodyEn": "How the look and behavior of Apple's interfaces change: new design languages, gestures, ways to navigate. This is the area where aesthetic choices become product choices, because an interface change reshapes the habits of millions of people.",
    },
    "spatial-visionos": {
        "h2It": "visionOS e lo spatial computing",
        "h2En": "visionOS and spatial computing",
        "bodyIt": "Il fronte più sperimentale: visionOS e tutto ciò che riguarda il computing spaziale. Qui si misura se Apple riesce a far uscire la categoria dalla nicchia degli early adopter — nuove funzioni, nuovi contenuti, nuovi strumenti per chi sviluppa esperienze immersive.",
        "bodyEn": "The most experimental front: visionOS and everything around spatial computing. Here we measure whether Apple can move the category beyond the early-adopter niche — new features, new content, new tools for those building immersive experiences.",
    },
    "salute-benessere": {
        "h2It": "Salute, fitness e watchOS",
        "h2En": "Health, fitness and watchOS",
        "bodyIt": "Uno dei terreni dove Apple ha costruito il vantaggio più solido. Raccolgo qui le novità su salute, attività fisica e watchOS: funzioni che, più di altre, toccano la vita quotidiana e i dati più sensibili delle persone. Con l'attenzione che meritano sia il valore sia le implicazioni.",
        "bodyEn": "One of the areas where Apple has built its most solid advantage. I gather here the news on health, fitness and watchOS: features that, more than others, touch daily life and people's most sensitive data. With the attention both the value and the implications deserve.",
    },
    "servizi-ecosistema": {
        "h2It": "iCloud, Continuity e l'ecosistema",
        "h2En": "iCloud, Continuity and the ecosystem",
        "bodyIt": "Il collante che tiene insieme i dispositivi Apple: iCloud, Continuity, i servizi e le funzioni che fanno parlare iPhone, Mac, iPad e Watch tra loro. È l'area meno appariscente ma spesso la più strategica, perché è qui che si rafforza (o si allenta) il lock-in dell'ecosistema.",
        "bodyEn": "The glue that holds Apple's devices together: iCloud, Continuity, the services and features that make iPhone, Mac, iPad and Watch talk to each other. The least flashy area but often the most strategic, because this is where the ecosystem lock-in tightens (or loosens).",
    },
    "privacy-sicurezza": {
        "h2It": "Privacy e sicurezza",
        "h2En": "Privacy and security",
        "bodyIt": "Privacy come argomento di marketing e come scelta architetturale. Qui seguo gli annunci che riguardano protezione dei dati, sicurezza e trasparenza — soprattutto nel punto delicato in cui l'AI on-device e quella in cloud si incontrano. Cosa promette Apple e come lo mantiene a livello tecnico.",
        "bodyEn": "Privacy as a marketing argument and as an architectural choice. Here I follow the announcements on data protection, security and transparency — especially at the delicate point where on-device and cloud AI meet. What Apple promises and how it holds up technically.",
    },
}

TAG_INTROS = {
    "intelligenza-artificiale": {
        "h2It": "Tutti gli articoli che toccano l'AI",
        "h2En": "All articles touching AI",
        "bodyIt": "L'intelligenza artificiale è il filo conduttore del WWDC 2026 e attraversa più aree contemporaneamente: sistemi operativi, sviluppo, salute, servizi. Sotto questo tag trovi tutti gli articoli del sito che affrontano direttamente la dimensione AI, dalle funzioni di prodotto alle scelte di architettura.",
        "bodyEn": "Artificial intelligence is the through-line of WWDC 2026 and cuts across several areas at once: operating systems, development, health, services. Under this tag you find every article on the site that directly engages the AI dimension, from product features to architectural choices.",
    },
    "siri": {
        "h2It": "Il nuovo Siri, annuncio per annuncio",
        "h2En": "The new Siri, announcement by announcement",
        "bodyIt": "Tutto ciò che riguarda Siri: nuove capacità, integrazioni, tempi di rilascio. Il tag da seguire per capire se il rilancio dell'assistente è reale o rinviato.",
        "bodyEn": "Everything about Siri: new capabilities, integrations, release timing. The tag to follow to understand whether the assistant's relaunch is real or postponed.",
    },
    "swift-xcode": {
        "h2It": "Swift, Xcode e gli strumenti di sviluppo",
        "h2En": "Swift, Xcode and developer tooling",
        "bodyIt": "Gli articoli dedicati al cuore tecnico del WWDC: linguaggio Swift, ambiente Xcode, framework e API. Per chi costruisce app, è qui che si decide la produttività dei prossimi mesi.",
        "bodyEn": "The articles devoted to WWDC's technical core: the Swift language, the Xcode environment, frameworks and APIs. For those building apps, this is where the productivity of the coming months is decided.",
    },
    "design": {
        "h2It": "Design e linguaggio visivo",
        "h2En": "Design and visual language",
        "bodyIt": "Il filone dedicato all'estetica e all'interazione: come cambiano forma e comportamento delle interfacce Apple, e cosa significa per chi progetta esperienze.",
        "bodyEn": "The thread devoted to aesthetics and interaction: how the form and behavior of Apple's interfaces change, and what it means for those designing experiences.",
    },
    "privacy": {
        "h2It": "Privacy e protezione dei dati",
        "h2En": "Privacy and data protection",
        "bodyIt": "Gli articoli che toccano la protezione dei dati e la trasparenza, trasversali a tutte le aree: dal sistema operativo all'AI ai servizi cloud.",
        "bodyEn": "The articles touching data protection and transparency, cutting across all areas: from the operating system to AI to cloud services.",
    },
    "salute": {
        "h2It": "Salute e benessere, trasversale",
        "h2En": "Health and wellbeing, cross-cutting",
        "bodyIt": "Tutto ciò che riguarda salute e attività fisica, sia sul Watch sia sulle altre piattaforme. Un filone che intreccia prodotto, dati sensibili e responsabilità.",
        "bodyEn": "Everything about health and physical activity, both on the Watch and across other platforms. A thread that weaves together product, sensitive data and responsibility.",
    },
    "continuity": {
        "h2It": "Continuity ed ecosistema",
        "h2En": "Continuity and ecosystem",
        "bodyIt": "Gli annunci che rendono più stretto il legame tra i dispositivi Apple: handoff, sincronizzazione, funzioni cross-device. Il tessuto connettivo dell'ecosistema.",
        "bodyEn": "The announcements that tighten the bond between Apple's devices: handoff, sync, cross-device features. The connective tissue of the ecosystem.",
    },
    "accessibilita": {
        "h2It": "Accessibilità",
        "h2En": "Accessibility",
        "bodyIt": "Le novità che rendono i dispositivi Apple usabili da più persone. Un'area spesso sottovalutata nella copertura mainstream ma centrale nella filosofia di prodotto.",
        "bodyEn": "The news that makes Apple's devices usable by more people. An area often underrated in mainstream coverage but central to the product philosophy.",
    },
}
