const fs = require('fs');
const os = require('os');
const path = require('path');
const readline = require('readline');
const promisify = require('util').promisify
const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});
const rlQuestion = promisify(rl.question).bind(rl);
const BASE_URL = "https://www.hepsiemlak.com"
const COOKIE_PATH = path.join(os.tmpdir(), "cookie_hepsiemlak.txt")
let cookie = fs.existsSync(COOKIE_PATH)?fs.readFileSync(COOKIE_PATH).toString():""
const ID_LIST_ENDPOINT = BASE_URL+"/api/realty-map/?mapSize=2500&intent=satilik&city=sakarya&mainCategory=konut&mapCornersEnabled=true"
const USER_AGENTS = [["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",0.1]]
const CAPTCHA_ERR = "Hata. Robot doğrulamasını geçmek gerekebilir.\nYönerge: https://github.com/arfelious/hepsiemlak-scraper/blob/main/captcha.md"
let getWeightedRandom = list=>{
    let totalWeight = list.reduce((a,c)=>a+c[1],0)
    let random = Math.random()*totalWeight
    for(let i=0;i<list.length;i++){
        random-=list[i][1]
        if(random<=0){
            return list[i][0]
        }
    }
}
let getRandomUserAgent = (osType) => {
    const filteredAgents = USER_AGENTS.filter(([os,]) => os.toLowerCase() === osType?.toLowerCase());
    return filteredAgents.length ? getWeightedRandom(filteredAgents) : getWeightedRandom(USER_AGENTS)
};
let extractUserAgent = (cookie) => {
    const match = cookie.match(/device_info=([^;]+)/);
    if (match) {
        try {
            const deviceInfo = JSON.parse(decodeURIComponent(match[1]));
            return deviceInfo.user_agent || null;
        } catch (e) {
            console.error("Error",e)
        }
    }
    return null;
};
let getOptions = (cookie)=>{
    let userAgent = extractUserAgent(cookie);
    if (!userAgent) {
        const osTypeMatch = cookie.match(/"os_type"\s*:\s*"([^"]+)"/);
        const osType = osTypeMatch ? osTypeMatch[1] : "Linux";
        userAgent = getRandomUserAgent(osType);
    }
    let res = {
        "headers": {
                "Referer": "https://www.hepsiemlak.com/tekirdag-kiralik/yazlik",
                "Referrer-Policy": "no-referrer-when-downgrade",
                "accept": "*/*",
                "accept-language": "tr-TR,tr;q=0.9",
                "cache-control": "no-cache",
                "pragma": "no-cache",
                "sec-ch-ua": "\"Not(A:Brand\";v=\"99\", \"Google Chrome\";v=\"133\", \"Chromium\";v=\"133\"",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "\"Windows\"",
                "sec-fetch-dest": "script",
                "sec-fetch-mode": "no-cors",
                "sec-fetch-site": "same-origin",
            "cookie": cookie,
            "Referer": "https://www.hepsiemlak.com/tekirdag-kiralik/yazlik"
        },
          "body": null,
        "method": "GET"
    }      
    return res
}
let getListingIds = async ()=>{
    let res = await sfetch(ID_LIST_ENDPOINT,getOptions(cookie))
    try{
        let curr = await res.text()
        if(curr.includes("Just a moment...")){
            throw CAPTCHA_ERR
        }
        try{
            let parsed = JSON.parse(curr)
            return parsed.realties.map(x=>x.listingId)
        }catch(e){
            console.error(e)
            throw "Hata. İlan ID'leri alınamadı.\nSunucudan gelen yanıt: "+curr.slice(0,50)+"..."
        }
    }
    catch(e){
        console.error(e)
    }
}
const IMG_EXTS = ["jpg","jpeg","png","gif","webp"]
let removeImages = obj=>{
    for(let key in obj){
        let val = obj[key]
        if(typeof val=="string"&&IMG_EXTS.some(x=>val.includes(x))){
            delete obj[key]
        }
        else if(typeof val == "object"){
            removeImages(val)
        }
    }
}
let getListing = async id=>{
    let res = await sfetch(BASE_URL+"/api/realties/"+id, getOptions(cookie))
    try{
        let curr = await res.text()
        if(curr.includes("Just a moment...")){
            throw CAPTCHA_ERR
        }
        try{
            let parsed = JSON.parse(curr)
            if(parsed.exception){
                throw "Hata. Sunucudan gelen hata mesajı: "+parsed.errors.join(", ")
                
            }
            let res = parsed.realtyDetail
            removeImages(res)
            delete res.breadcrumbs
            return JSON.stringify(res)
        }catch(e){
            throw e.startsWith("Hata")?e:"Hata. İlan bilgileri alınamadı.\nSunucudan gelen yanıt: "+curr.slice(0,50)+"..."
        }
    }catch(e){
        console.error(e)
    }
}
let cookieStore = {}; 
function parseSetCookie(setCookieHeaders,isInitial) {
    if (!setCookieHeaders) return;
    const cookies = Array.isArray(setCookieHeaders) ? setCookieHeaders : [setCookieHeaders];

    cookies.forEach(cookie => {
        const parts = cookie.split(";");
        parts.forEach(part=>{
            const [name, value] = part.trim().split("=");
            if(name=="path"||name=="expires"||name=="domain"||name=="SameSite")return
            if (name && value){
                cookieStore[name.trim()] = value.trim();
            }
        })

    });
}
parseSetCookie(cookie,true)
function getCookieHeader() {
    return Object.entries(cookieStore).map(([key, value]) => `${key}=${value}`).join("; ");
}
let sleep = ms=>new Promise(res=>setTimeout(res,ms))
async function sfetch(url, options = {}, depth = 0) {
    options.redirect = "manual";
    if (!options.headers) options.headers = {};
    options.headers["Cookie"] = getCookieHeader(); 
    let response = await fetch(url, options)
    if (response.headers.has("set-cookie")) {
        parseSetCookie(response.headers.get("set-cookie"));
    }
    if (response.status === 403&&depth<5) {
        let text = await response.text()
        const location = response.headers.get("location")||BASE_URL+text.split('fa: "')[1].split('"')[0].replace(/\\/g,"")
        await sleep(5000+Math.random()*2000)
        return sfetch(new URL(location, url).toString(), options, depth + 1);
    }

    return response;
}

let start = async ()=>{
    let curr = await rlQuestion("İşlem: (al/listele/cookie): ")
    curr=curr.trim().toLocaleLowerCase()
    switch(curr){
        case "al":{
            let id = (await rlQuestion("İlan ID:"))?.trim()
            let listing = await getListing(id)
            console.log(listing)
            break
        }
        case "listele":{
            let ids = await getListingIds()
            let max = Math.floor(process.stdout.columns/16)
            let str = ""
            if(!ids)break
            for(let i=0;i<ids.length;i++){
                str+=ids[i].padStart(15," ")+" "
                if(i%max==0){
                    console.log(str)
                    str=""
                }
            }
            console.log("Listelenen ilanların başkaları tarafından alınmadığını kontrol etmeyi unutmayın.")
            break
        }
        case "cookie":{
            let newCookie = await rlQuestion("Cookie: ")
            parseSetCookie(newCookie,true)
            fs.writeFileSync(COOKIE_PATH, newCookie)
            cookie = newCookie
            break
        }
        default:
            console.log("Geçersiz işlem.")
    } 
    start()
}
start()