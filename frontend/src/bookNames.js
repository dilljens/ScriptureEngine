/**
 * Book name resolution and reference formatting.
 *
 * Provides:
 *  - parseRef(ref) → { label, book, chapter, verse, bookName, workId } or null
 *  - formatRef(book, chapter, verse) → "book.chapter.verse"
 */

// Which work each book belongs to
const WORK_MAP = {
  // OT
  gen:'ot', exo:'ot', lev:'ot', num:'ot', deu:'ot',
  josh:'ot', judg:'ot', ruth:'ot',
  '1sam':'ot', '2sam':'ot', '1kgs':'ot', '2kgs':'ot',
  '1chr':'ot', '2chr':'ot', ezra:'ot', neh:'ot',
  esth:'ot', job:'ot', psa:'ot', prov:'ot', eccl:'ot', song:'ot',
  isa:'ot', jer:'ot', lam:'ot', ezek:'ot', dan:'ot',
  hos:'ot', joel:'ot', amos:'ot', obad:'ot', jonah:'ot',
  mic:'ot', nah:'ot', hab:'ot', zeph:'ot', hag:'ot', zech:'ot', mal:'ot',
  // Apocrypha
  tob:'apoc', jdt:'apoc', wis:'apoc', sir:'apoc', bar:'apoc',
  '1ma':'apoc', '2ma':'apoc', '1esd':'apoc', '2esd':'apoc',
  man:'apoc', sus:'apoc', bel:'apoc', s3y:'apoc', esga:'apoc', psa151:'apoc',
  // NT
  matt:'nt', mark:'nt', luke:'nt', john:'nt', acts:'nt',
  rom:'nt', '1cor':'nt', '2cor':'nt', gal:'nt', eph:'nt',
  phil:'nt', col:'nt', '1thes':'nt', '2thes':'nt',
  '1tim':'nt', '2tim':'nt', titus:'nt', philem:'nt',
  heb:'nt', james:'nt', '1pet':'nt', '2pet':'nt',
  '1john':'nt', '2john':'nt', '3john':'nt', jude:'nt', rev:'nt',
  // BoM
  '1ne':'bom', '2ne':'bom', jacob:'bom', enos:'bom', jarom:'bom',
  omni:'bom', wom:'bom', mosiah:'bom', alma:'bom', hel:'bom',
  '3ne':'bom', '4ne':'bom', morm:'bom', ether:'bom', moro:'bom',
  // PGP
  moses:'pgp', abraham:'pgp', jsm:'pgp', jsh:'pgp', aoff:'pgp',
  // DSS
  '1QS':'dss', '1QSa':'dss', '1QSb':'dss', '1QM':'dss',
  '1QHa':'dss', '1QpHab':'dss', '11Q13':'dss', '11Q19':'dss', '11Q20':'dss',
  'CD':'dss', '4Q400':'dss', '4Q401':'dss', '4Q402':'dss', '4Q403':'dss',
  '4Q404':'dss', '4Q405':'dss', '4Q406':'dss', '4Q407':'dss',
  '4Q174':'dss', '4Q246':'dss', '4Q521':'dss',
  '4Q266':'dss', '4Q267':'dss', '4Q268':'dss', '4Q269':'dss',
  '4Q270':'dss', '4Q271':'dss', '4Q272':'dss', '4Q273':'dss',
  '4Q394':'dss', '4Q395':'dss', '4Q396':'dss', '4Q397':'dss',
  '4Q398':'dss', '4Q399':'dss',
  '1Qisaa':'dss', '1Q20':'dss', bookgiants:'dss', visamram:'dss', tkohath:'dss',
  // Pseudepigrapha
  '1en':'pseu', '2en':'pseu', '3bar':'pseu', '4bar':'pseu',
  '1adae':'pseu', '2adae':'pseu', apabr:'pseu', apelj:'pseu',
  apsed:'pseu', apjosh:'pseu', ascis:'pseu', asmos:'pseu',
  azar:'pseu', balin:'pseu', jasher:'pseu', jub:'pseu',
  nathan:'pseu', '5psdav':'pseu', gad:'pseu', grkest:'pseu',
  rechab:'pseu', janjam:'pseu', josasen:'pseu', ladjac:'pseu',
  livprop:'pseu', odessol:'pseu', psssol:'pseu',
  tabr:'pseu', tisaac:'pseu', tjacob:'pseu', tjob:'pseu',
  tsol:'pseu', ahikar:'pseu',
  treub:'pseu', tsimeon:'pseu', tlevi:'pseu', tjudah:'pseu',
  tdan:'pseu', tnaph:'pseu', tgad:'pseu', tasher:'pseu',
  tiss:'pseu', tzeb:'pseu', tjos:'pseu', tbenj:'pseu',
  // Expanded Canon
  '1her':'expanded', '2her':'expanded', '3her':'expanded',
  apet:'expanded', barn:'expanded', gnic:'expanded',
}

// Full book titles
export const BOOK_TITLES = {
  gen:'Genesis', exo:'Exodus', lev:'Leviticus', num:'Numbers', deu:'Deuteronomy',
  josh:'Joshua', judg:'Judges', ruth:'Ruth',
  '1sam':'1 Samuel', '2sam':'2 Samuel', '1kgs':'1 Kings', '2kgs':'2 Kings',
  '1chr':'1 Chronicles', '2chr':'2 Chronicles',
  ezra:'Ezra', neh:'Nehemiah', esth:'Esther', job:'Job',
  psa:'Psalms', prov:'Proverbs', eccl:'Ecclesiastes', song:'Song of Solomon',
  isa:'Isaiah', jer:'Jeremiah', lam:'Lamentations', ezek:'Ezekiel', dan:'Daniel',
  hos:'Hosea', joel:'Joel', amos:'Amos', obad:'Obadiah', jonah:'Jonah',
  mic:'Micah', nah:'Nahum', hab:'Habakkuk', zeph:'Zephaniah', hag:'Haggai',
  zech:'Zechariah', mal:'Malachi',
  tob:'Tobit', jdt:'Judith', wis:'Wisdom of Solomon', sir:'Sirach',
  bar:'Baruch', '1ma':'1 Maccabees', '2ma':'2 Maccabees',
  '1esd':'1 Esdras', '2esd':'2 Esdras',
  man:'Prayer of Manasses', sus:'Susanna', bel:'Bel and the Dragon',
  s3y:'Song of Three Children', esga:'Additions to Esther', psa151:'Psalm 151',
  matt:'Matthew', mark:'Mark', luke:'Luke', john:'John',
  acts:'Acts', rom:'Romans', '1cor':'1 Corinthians', '2cor':'2 Corinthians',
  gal:'Galatians', eph:'Ephesians', phil:'Philippians', col:'Colossians',
  '1thes':'1 Thessalonians', '2thes':'2 Thessalonians',
  '1tim':'1 Timothy', '2tim':'2 Timothy', titus:'Titus', philem:'Philemon',
  heb:'Hebrews', james:'James', '1pet':'1 Peter', '2pet':'2 Peter',
  '1john':'1 John', '2john':'2 John', '3john':'3 John', jude:'Jude', rev:'Revelation',
  '1ne':'1 Nephi', '2ne':'2 Nephi', jacob:'Jacob', enos:'Enos',
  jarom:'Jarom', omni:'Omni', wom:'Words of Mormon',
  mosiah:'Mosiah', alma:'Alma', hel:'Helaman',
  '3ne':'3 Nephi', '4ne':'4 Nephi', morm:'Mormon',
  ether:'Ether', moro:'Moroni',
  moses:'Moses', abraham:'Abraham', jsm:'Joseph Smith—Matthew',
  jsh:'Joseph Smith—History', aoff:'Articles of Faith',
  // DSS
  '1QS':'Community Rule', '1QSa':'Rule of the Congregation',
  '1QSb':'Rule of the Blessings', '1QM':'War Scroll',
  '1QHa':'Thanksgiving Hymns', '1QpHab':'Pesher Habakkuk',
  '11Q13':'Melchizedek Scroll', '11Q19':'Temple Scroll',
  '11Q20':'Temple Scroll (fragment)', 'CD':'Damascus Document',
  '4Q400':'Songs of Sabbath Sacrifice', '4Q401':'Songs of Sabbath Sacrifice',
  '4Q402':'Songs of Sabbath Sacrifice', '4Q403':'Songs of Sabbath Sacrifice',
  '4Q404':'Songs of Sabbath Sacrifice', '4Q405':'Songs of Sabbath Sacrifice',
  '4Q406':'Songs of Sabbath Sacrifice', '4Q407':'Songs of Sabbath Sacrifice',
  '4Q174':'Florilegium', '4Q246':'Son of God Apocalypse',
  '4Q521':'Messianic Apocalypse',
  '4Q266':'Damascus Document', '4Q267':'Damascus Document',
  '4Q268':'Damascus Document', '4Q269':'Damascus Document',
  '4Q270':'Damascus Document', '4Q271':'Damascus Document',
  '4Q272':'Damascus Document', '4Q273':'Damascus Document',
  '4Q394':'4QMMT', '4Q395':'4QMMT', '4Q396':'4QMMT',
  '4Q397':'4QMMT', '4Q398':'4QMMT', '4Q399':'4QMMT',
  '1Qisaa':'Isaiah Scroll', '1Q20':'Genesis Apocryphon',
  bookgiants:'Book of Giants', visamram:'Visions of Amram',
  tkohath:'Testament of Kohath',
  // Pseudepigrapha
  '1en':'1 Enoch', '2en':'2 Enoch', '3bar':'3 Baruch',
  '4bar':'4 Baruch',
  '1adae':'Life of Adam and Eve', '2adae':'Apocalypse of Adam and Eve',
  apabr:'Apocalypse of Abraham', apelj:'Apocalypse of Elijah',
  apsed:'Apocalypse of Sedrach', apjosh:'Apocryphon of Joshua',
  ascis:'Ascension of Isaiah', asmos:'Assumption of Moses',
  azar:'Prayer of Azariah', balin:'Balaam Inscription',
  jasher:'Book of Jasher', jub:'Jubilees',
  nathan:'Book of Nathan', '5psdav':'Five Psalms of David',
  gad:'Gad the Seer', grkest:'Greek Esther',
  rechab:'History of the Rechabites', janjam:'Jannes and Jambres',
  josasen:'Joseph and Asenath', ladjac:'Ladder of Jacob',
  livprop:'Lives of the Prophets', odessol:'Odes of Solomon',
  psssol:'Psalms of Solomon',
  tabr:'Testament of Abraham', tisaac:'Testament of Isaac',
  tjacob:'Testament of Jacob', tjob:'Testament of Job',
  tsol:'Testament of Solomon', ahikar:'Wisdom of Ahikar',
  treub:'Testament of Reuben', tsimeon:'Testament of Simeon',
  tlevi:'Testament of Levi', tjudah:'Testament of Judah',
  tdan:'Testament of Dan', tnaph:'Testament of Naphtali',
  tgad:'Testament of Gad', tasher:'Testament of Asher',
  tiss:'Testament of Issachar', tzeb:'Testament of Zebulun',
  tjos:'Testament of Joseph', tbenj:'Testament of Benjamin',
  // Expanded Canon
  '1her':'Shepherd of Hermas — Visions',
  '2her':'Shepherd of Hermas — Mandates',
  '3her':'Shepherd of Hermas — Similitudes',
  apet:'Apocalypse of Peter', barn:'Epistle of Barnabas',
  gnic:'Gospel of Nicodemus',
}

/**
 * Parse a verse reference string like "gen.1.1" or "gen.1" into its components.
 * Returns { label, book, chapter, verse, bookName, workId } or null.
 */
export function parseRef(ref) {
  if (!ref) return null

  // Handle D&C sections: "dc76.1" or "dc76"
  const dcMatch = ref.match(/^(dc)(\d+)(?:\.(\d+))?$/)
  if (dcMatch) {
    const book = `dc${dcMatch[2]}`
    const chapter = 1
    const verse = dcMatch[3] ? parseInt(dcMatch[3]) : null
    const label = `D&C ${dcMatch[2]}${verse ? `:${verse}` : ''}`
    return { label, book, chapter, verse, bookName: `D&C ${dcMatch[2]}`, workId: 'dc' }
  }

  const parts = ref.split('.')
  if (parts.length < 2) return null

  const bookId = parts[0].toLowerCase()
  const chapter = parseInt(parts[1])
  const verse = parts[2] ? parseInt(parts[2]) : null

  if (isNaN(chapter)) return null

  const bookTitle = BOOK_TITLES[bookId]
  if (!bookTitle) return null

  // Determine workId (D&C books are stored as dcN)
  let workId = WORK_MAP[bookId]
  if (!workId && bookId.startsWith('dc')) workId = 'dc'

  let label = `${bookTitle} ${chapter}`
  if (verse != null) label += `:${verse}`

  return { label, book: bookId, chapter, verse, bookName: bookTitle, workId }
}

/**
 * Format a book/chapter/verse into a reference string.
 */
export function formatRef(book, chapter, verse) {
  if (verse != null) return `${book}.${chapter}.${verse}`
  return `${book}.${chapter}`
}
