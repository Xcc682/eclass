const fs = require('node:fs')
const path = require('node:path')
const sharp = require('sharp')

const assetDirectory = path.resolve(__dirname, '../src/assets/immersive')
const books = [
  'history-1', 'history-2', 'history-3', 'history-4', 'history-5',
  'tour-1', 'tour-2', 'tour-3', 'tour-4', 'tour-5',
]
const cells = [
  ['route', 1], ['route', 2],
  ['evidence', 1], ['evidence', 2],
  ['judgment', 1], ['judgment', 2],
]

async function buildBook(bookId) {
  const source = path.join(assetDirectory, `${bookId}-detours.png`)
  if (!fs.existsSync(source)) throw new Error(`Missing generated atlas: ${source}`)
  const metadata = await sharp(source).metadata()
  if (!metadata.width || !metadata.height) throw new Error(`Invalid atlas dimensions: ${source}`)

  for (let cell = 0; cell < cells.length; cell += 1) {
    const column = cell % 3
    const row = Math.floor(cell / 3)
    const left = Math.round(metadata.width * column / 3)
    const right = Math.round(metadata.width * (column + 1) / 3)
    const top = Math.round(metadata.height * row / 2)
    const bottom = Math.round(metadata.height * (row + 1) / 2)
    const [stage, branch] = cells[cell]
    const target = path.join(assetDirectory, `${bookId}-detour-${stage}-${branch}.webp`)
    await sharp(source)
      .extract({ left, top, width: right - left, height: bottom - top })
      .webp({ quality: 86, smartSubsample: true })
      .toFile(target)
  }
}

Promise.all(books.map(buildBook))
  .then(() => console.log(`Built ${books.length * cells.length} immersive detour WebP assets.`))
  .catch(error => {
    console.error(error)
    process.exitCode = 1
  })
