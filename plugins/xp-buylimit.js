const xpperlimit = 350 
let handler = async (m, { conn, command, args }) => {
  let ftroli = {
    key : {
    remoteJid: '',
    participant : '0@s.whatsapp.net'
    },
    message: {
    orderMessage: {
    itemCount : 2024,
    status: 1,
    surface : 1,
    message: 'Get Limit', 
    orderTitle: `Iky𝖔𝖋𝖋𝖎𝖈𝖎𝖆𝖑ཽ`,
    thumbnail: 'https://telegra.ph/file/e518f1ae5447bc820c741.jpg', 
    sellerJid: '0@s.whatsapp.net' 
    }
    }
    }
  let count = command.replace(/^buy/i, '')
  count = count ? /all/i.test(count) ? Math.floor(global.db.data.users[m.sender].exp / xpperlimit) : parseInt(count) : args[0] ? parseInt(args[0]) : 1
  count = Math.max(1, count)
  if (global.db.data.users[m.sender].exp >= xpperlimit * count) {
    global.db.data.users[m.sender].exp -= xpperlimit * count
    global.db.data.users[m.sender].limit += count
    conn.reply(m.chat, `Berhasil Membeli ${count} Limit 🏷 Dengan ${xpperlimit * count} Xp 🧬`, ftroli) 
  } else conn.reply(m.chat, `XP anda tidak mencukupi untuk membeli ${count} limit, Anda dapat menambah exp dengan bermain game dan rpg`, ftroli) 
}
handler.help = ['buy<jumlah limit>', 'buy <jumlah limit>', 'buyall']
handler.tags = ['xp']
handler.command = /^buylimit([0-9]+)|buylimit|buyalllimit$/i
handler.owner = false
handler.mods = false
handler.premium = false
handler.group = false
handler.private = false

handler.admin = false
handler.botAdmin = false

handler.fail = null
handler.exp = 0

module.exports = handler