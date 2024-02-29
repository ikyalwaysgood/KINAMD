let moment = require('moment-timezone')
let handler = async (m, {conn}) => {
    let _uptime = process.uptime() * 1000
    let uptime = clockString(_uptime)
    let d = new Date
    let date = d.toLocaleDateString('id', {
        day: 'numeric',
        month: 'long',
        year: 'numeric'
    })
let anu = `${ucapan()}
Hallo👋
Ada Yang Bisa Kιɳα Bσƚ Bantu?
Ketik .menu Untuk Memulai Kιɳα Bσƚ
Ketik .owner Untuk Menghubungi Owner

Runtime: ${uptime}`
   const ftroli = {
    key : {
    remoteJid: '',
    participant : '0@s.whatsapp.net'
    },
    message: {
    orderMessage: {
    itemCount : 2024,
    status: 1,
    surface : 1,
    message: `2024 © ${namebot}`, 
    orderTitle: `Iky𝖔𝖋𝖋𝖎𝖈𝖎𝖆𝖑ཽ`,
    thumbnail: 'https://telegra.ph/file/e518f1ae5447bc820c741.jpg', 
    sellerJid: '0@s.whatsapp.net' 
    }
    }
    }
   conn.reply(m.chat, anu, ftroli) 
}
handler.customPrefix = /^bot$/i // ketik bot (tanpa prefix)
handler.command = new RegExp
handler.owner = false
handler.mods = false
handler.premium = false
handler.group = false
handler.private = false
handler.admin = false
handler.botAdmin = false
handler.fail = null
module.exports = handler

function ucapan() {
  const time = moment.tz('Asia/Jakarta').format('HH')
  if (time >= 5) {
    res = "Selamat pagi🌄"
  }
  if (time > 9) {
    res = "Selamat siang🏞️"
  }
  if (time >= 15) {
    res = "Selamat sore🌇"
  }
  if (time >= 19) {
    res = "Selamat malam🌃"
  }
  return res
}
function clockString(ms) {
    let h = isNaN(ms) ? '--' : Math.floor(ms / 3600000)
    let m = isNaN(ms) ? '--' : Math.floor(ms / 60000) % 60
    let s = isNaN(ms) ? '--' : Math.floor(ms / 1000) % 60
    return [h, m, s].map(v => v.toString().padStart(2, 0)).join(':')
}
