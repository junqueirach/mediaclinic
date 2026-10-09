# =============================================================================
# genre_data.py
# Metadata & MediaClinic — Genre synonym and translation tables (pure data)
# Version: 0.18.3                                              ### NEW v0.18.3 ###
# Author:  Luiz Junqueira & Claude AI
#
# Moved out of the main script in v0.18.3 to keep it smaller.  Content is
# identical to v0.18.2 (_GENRE_SYNONYMS and _GENRE_TRANSLATIONS).
# No imports, no logic — data only.
# =============================================================================

# Synonym → canonical name mapping (TMDb authoritative)
GENRE_SYNONYMS = {
    "sci-fi": "Science Fiction", "scifi": "Science Fiction",
    "sci fi": "Science Fiction", "science-fiction": "Science Fiction",
    "sf": "Science Fiction",
    "docu": "Documentary", "docs": "Documentary",
    "romance": "Romance", "romantic": "Romance",
    "musical": "Music",
    "biopic": "History", "bio": "History",
    "suspense": "Thriller",
    "sport": "Action", "sports": "Action",
    "animation": "Animation", "animated": "Animation",
    "action & adventure": "Action",
    "kids": "Family", "children": "Family",
}

# Multilingual genre translation dictionary (v0.16.0)
# Covers PT, DE, FR, ES, IT, RU, ZH (Mandarin), AR
# Maps foreign-language genre names (lowercase) → English canonical name
GENRE_TRANSLATIONS = {
    # Portuguese
    "ação": "Action", "accao": "Action", "acao": "Action",
    "aventura": "Adventure", "animação": "Animation", "animacao": "Animation",
    "comédia": "Comedy", "comedia": "Comedy", "crime": "Crime",
    "documentário": "Documentary", "documentario": "Documentary",
    "drama": "Drama", "família": "Family", "familia": "Family",
    "fantasia": "Fantasy", "história": "History", "historia": "History",
    "terror": "Horror", "horror": "Horror", "música": "Music", "musica": "Music",
    "mistério": "Mystery", "misterio": "Mystery",
    "romance": "Romance", "romântico": "Romance", "romantico": "Romance",
    "ficção científica": "Science Fiction", "ficcao cientifica": "Science Fiction",
    "fc": "Science Fiction", "suspense": "Thriller", "guerra": "War",
    "faroeste": "Western", "ocidental": "Western",
    # German
    "aktion": "Action", "abenteuer": "Adventure",
    "animation": "Animation", "komödie": "Comedy", "komodie": "Comedy",
    "kriminalfilm": "Crime", "krimi": "Crime", "dokumentarfilm": "Documentary",
    "doku": "Documentary", "familie": "Family", "fantasie": "Fantasy",
    "geschichte": "History", "horror": "Horror", "musik": "Music",
    "geheimnis": "Mystery", "liebesfilm": "Romance", "romantik": "Romance",
    "wissenschaftliche fiktion": "Science Fiction", "science-fiction": "Science Fiction",
    "thriller": "Thriller", "krieg": "War", "western": "Western",
    # French
    "action": "Action", "aventure": "Adventure",
    "comédie": "Comedy", "comedie": "Comedy", "policier": "Crime",
    "documentaire": "Documentary", "drame": "Drama", "famille": "Family",
    "fantastique": "Fantasy", "histoire": "History", "horreur": "Horror",
    "musique": "Music", "mystère": "Mystery", "mystere": "Mystery",
    "romance": "Romance", "science-fiction": "Science Fiction",
    "sf": "Science Fiction", "guerre": "War", "western": "Western",
    # Spanish
    "acción": "Action", "accion": "Action", "aventura": "Adventure",
    "animación": "Animation", "animacion": "Animation",
    "comedia": "Comedy", "crimen": "Crime", "documental": "Documentary",
    "drama": "Drama", "familia": "Family", "fantasía": "Fantasy", "fantasia": "Fantasy",
    "historia": "History", "terror": "Horror", "música": "Music", "musica": "Music",
    "misterio": "Mystery", "romance": "Romance", "ciencia ficción": "Science Fiction",
    "ciencia ficcion": "Science Fiction", "suspenso": "Thriller", "guerra": "War",
    "vaquero": "Western",
    # Italian
    "azione": "Action", "avventura": "Adventure", "animazione": "Animation",
    "commedia": "Comedy", "crimine": "Crime", "documentario": "Documentary",
    "dramma": "Drama", "famiglia": "Family", "fantasia": "Fantasy",
    "storia": "History", "orrore": "Horror", "musica": "Music",
    "mistero": "Mystery", "romantico": "Romance", "fantascienza": "Science Fiction",
    "thriller": "Thriller", "guerra": "War", "western": "Western",
    # Russian (transliterated)
    "боевик": "Action", "boyevik": "Action", "приключения": "Adventure",
    "priklyucheniya": "Adventure", "мультфильм": "Animation",
    "комедия": "Comedy", "komediya": "Comedy", "криминал": "Crime",
    "dokumentalny": "Documentary", "драма": "Drama", "drama": "Drama",
    "семейный": "Family", "фэнтези": "Fantasy", "история": "History",
    "ужасы": "Horror", "uzhasy": "Horror", "музыка": "Music",
    "мистика": "Mystery", "mistika": "Mystery", "мелодрама": "Romance",
    "melodrama": "Romance", "фантастика": "Science Fiction",
    "fantastika": "Science Fiction", "триллер": "Thriller", "война": "War",
    "voyna": "War", "вестерн": "Western",
    # Chinese/Mandarin (common pinyin and hanzi)
    "动作": "Action", "dongzuo": "Action", "冒险": "Adventure",
    "maoxian": "Adventure", "动画": "Animation", "donghua": "Animation",
    "喜剧": "Comedy", "xiju": "Comedy", "犯罪": "Crime", "fanzui": "Crime",
    "纪录片": "Documentary", "jilupian": "Documentary",
    "剧情": "Drama", "juqing": "Drama", "家庭": "Family", "jiating": "Family",
    "奇幻": "Fantasy", "qihuan": "Fantasy", "历史": "History", "lishi": "History",
    "恐怖": "Horror", "kongbu": "Horror", "音乐": "Music", "yinyue": "Music",
    "悬疑": "Mystery", "xuanyi": "Mystery", "爱情": "Romance", "aiqing": "Romance",
    "科幻": "Science Fiction", "kehuan": "Science Fiction",
    "惊悚": "Thriller", "jingsong": "Thriller", "战争": "War", "zhanzheng": "War",
    "西部": "Western", "xibu": "Western",
    # Arabic (transliterated common terms)
    "اكشن": "Action", "akshun": "Action", "مغامرة": "Adventure",
    "mughamara": "Adventure", "كوميديا": "Comedy", "kumidya": "Comedy",
    "جريمة": "Crime", "jarima": "Crime", "وثائقي": "Documentary",
    "wathaiqi": "Documentary", "دراما": "Drama", "drama": "Drama",
    "عائلي": "Family", "ailiy": "Family", "خيال": "Fantasy", "khayal": "Fantasy",
    "تاريخي": "History", "tarikhi": "History", "رعب": "Horror", "ruub": "Horror",
    "موسيقى": "Music", "musiqa": "Music", "غموض": "Mystery", "ghumud": "Mystery",
    "رومانسي": "Romance", "rumansiy": "Romance",
    "خيال علمي": "Science Fiction", "khayal ilmi": "Science Fiction",
    "إثارة": "Thriller", "ithara": "Thriller", "حرب": "War", "harb": "War",
    "غربي": "Western", "gharbi": "Western",
}
