const fs=require('fs');
const html=fs.readFileSync('customer-history.html','utf8');
const scripts=html.match(/<script>([\s\S]*?)<\/script>/g)||[];
scripts.forEach((s,i)=>{
  const code=s.replace(/^<script>|<\/script>$/g,'');
  try{new Function(code);console.log('Script '+i+': OK ('+code.length+' chars)')}
  catch(e){console.log('Script '+i+' ERROR: '+e.message)}
});
