let fetch = require('node-fetch')
let handler = async (m, { conn }) => {
  let pepe = 'https://telegra.ph/file/e518f1ae5447bc820c741.jpg'
  let baper = await fetch(pepe).then(a => a.buffer())

  let diimz = '6285794908894@s.whatsapp.net'
  let a = await conn.profilePictureUrl(conn.user.jid, 'image').catch((_) => "https://telegra.ph/file/24fa902ead26340f3df2c.png")
  let b = await conn.profilePictureUrl(owner[0]+'@s.whatsapp.net', 'image').catch((_) => "https://telegra.ph/file/24fa902ead26340f3df2c.png")
  let c = pickRandom([a, b])
  let d = await fetch(c).then(a => a.buffer())
  let prepare = await require('@adiwajshing/baileys').generateWAMessageFromContent(m.key.remoteJid,{listMessage:{
  title: `${await conn.getName(conn.user.jid)}`,
  description: ` *• SEWA OWNER/GROUP & UP TO PREMIUM •*
        
1.  Owner / 30 Hari
Rp. 30.000 Gopay
Rp. 30.000 Pulsa

2. Grup / 30 Hari
Rp. 20.000 Gopay
Rp. 20.000 Pulsa

3. Premium / 30 Hari
Rp. 15.000 Gopay
Rp. 15.000 Pulsa

4. Premium + Grup / 30 Hari
Rp. 30.000 Gopay
Rp. 30.000 Pulsa

wa.me/${owner[0]}
*Bukan Bot!!!* 

*Owner ${conn.user.name}*
`,
  buttonText: 'Harga Sesuai Pasaran',
  listType: 2,
  productListInfo: {
  productSections: [{
  title:'Klik untuk order',
  products:[{productId:'7487741964584083'}]}],
  headerImage: { productId: '7487741964584083',
  jpegThumbnail: baper },
  businessOwnerJid: `6285794908894@s.whatsapp.net`
  },
  footerText: '©Iky𝖔𝖋𝖋𝖎𝖈𝖎𝖆𝖑ཽ',
  }},{})
  conn.relayMessage(prepare.key.remoteJid,prepare.message,{messageId:prepare.key.id})
  conn.sendContact(m.chat, numberowner, nameowner, m)
  
}
handler.help = ['sewa']
handler.tags = ['main']
handler.command = /^(sewa)$/i

module.exports = handler

function pickRandom(list) {
        return list[Math.floor(Math.random() * list.length)]
    }
