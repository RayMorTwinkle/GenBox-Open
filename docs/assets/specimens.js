/* All three samples are original, self-contained documents. Opening a sample
   does not create a publication. The downloaded bytes match the source view. */
const samples = {
  svg: {
    file: "ridge.svg",
    mime: "image/svg+xml",
    text: ridgeMap()
  },
  html: {
    file: "field-letter.html",
    mime: "text/html",
    text: `<!doctype html>
<html lang="zh-CN">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>山脊来信</title>
<style>
  * { box-sizing: border-box }
  body { margin: 0; min-height: 100vh; display: grid; align-content: center;
    padding: 7%; color: #313e35; background: #edf0df;
    font: clamp(13px, 3.2vw, 23px)/1.7 "Songti SC", serif }
  header { display: flex; gap: 12px; justify-content: space-between;
    padding-bottom: .7em; border-bottom: 1px solid #929b82;
    font: 600 .75em/1.5 system-ui, sans-serif; letter-spacing: .12em }
  h1 { font-size: 2.35em; line-height: 1.15; margin: .6em 0 .25em }
  p { margin: .3em 0; max-width: 27em }
  footer { margin-top: 1.1em; color: #536251; font-size: .83em }
</style>
<header><span>沿山来信</span><span>FIELD LETTER</span></header>
<h1>在山脊等风。</h1>
<p>松树在转弯处让开一小片天空。我们把地图折到下一面，沿山脊继续走。</p>
<footer>致同行的朋友 · 一张虚构的旅行明信片</footer>
</html>`
  },
  md: {
    file: "walking-notes.md",
    mime: "text/markdown",
    text: `# 清晨出发

约在山脚的石阶见。路书、地图和明信片，都放进同一个信封。

## 随身清单

- 水壶与一份干粮
- 折好的路线图
- 记录天气的小本子`
  }
};

function ridgeMap() {
  const contour = "M-152 12C-143-18-137-21-131-50S-112-82-86-87-55-99-39-114-6-113 9-108 41-119 60-102 64-83 89-73 98-49 122-36 148-22 146 0 164 32 138 49 131 77 100 80 71 109 49 106 25 125 3 113-28 119-45 102-74 99-89 81-116 85-121 60-153 48-152 12Z";
  const rings = (cx, cy, sx, sy, angle, n) => {
    const paths = Array.from({length: n}, (_, i) => {
      const k = 0.16 + i * 0.105;
      const major = (i + 1) % 4 === 0;
      return `    <use href="#contour" transform="rotate(${i * 1.05}) scale(${k.toFixed(3)})" fill="none" stroke="${major ? "#536654" : "#86917b"}" stroke-width="${major ? 1.5 : 0.85}" vector-effect="non-scaling-stroke"/>`;
    });
    return `  <g transform="translate(${cx} ${cy}) rotate(${angle}) scale(${sx} ${sy})">\n${paths.join("\n")}\n  </g>`;
  };

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 780 510" role="img" aria-labelledby="title desc">
  <title id="title">听山径，一张虚构的步行路线图</title>
  <desc id="desc">朱红色路线从溪桥经过鞍部，抵达东北侧的望海台。</desc>
  <defs>
    <pattern id="grid" width="34" height="34" patternUnits="userSpaceOnUse"><path d="M34 0H0V34" fill="none" stroke="#9a9e87" stroke-width=".75" opacity=".47"/></pattern>
    <path id="contour" d="${contour}"/>
  </defs>
  <rect width="780" height="510" fill="#eae8d2"/>
  <rect width="780" height="510" fill="url(#grid)"/>
  <g opacity=".92">
${rings(515, 207, 1.55, 1, -37, 19)}
${rings(166, 467, 0.9, 0.48, -27, 12)}
  </g>
  <path d="M-8 372C68 385 76 342 125 363S188 360 227 355 287 397 335 410 399 441 416 492L425 525" fill="none" stroke="#658381" stroke-width="3" opacity=".85"/>
  <path d="M216 367Q247 309 274 313T325 305 386 281 428 243 477 230 511 194 558 176 589 150 596 99" fill="none" stroke="#f7efcf" stroke-width="11" stroke-linecap="round"/>
  <path d="M216 367Q247 309 274 313T325 305 386 281 428 243 477 230 511 194 558 176 589 150 596 99" fill="none" stroke="#ad4837" stroke-width="5" stroke-linecap="round"/>
  <g fill="#fff3db" stroke="#893a2c" stroke-width="3"><circle cx="216" cy="367" r="7"/><circle cx="428" cy="243" r="6"/><circle cx="596" cy="99" r="7"/></g>
  <g font-family="'PingFang SC','Microsoft YaHei',sans-serif" font-size="20" fill="#452e28" stroke="#edead6" stroke-width="6" paint-order="stroke" stroke-linejoin="round">
    <text x="229" y="389">溪桥</text><text x="438" y="265">鞍部</text><text x="609" y="97">望海台</text>
  </g>
  <g transform="translate(22 25)" fill="#332f23">
    <rect width="239" height="119" rx="2" fill="#f8f2e4" stroke="#a9a18b"/>
    <text x="17" y="29" font-size="14" font-family="monospace" letter-spacing="2" fill="#695f49">WALKING ATLAS</text>
    <text x="15" y="81" font-family="'Songti SC','STSong',serif" font-size="49" font-weight="650" letter-spacing="3">听山径</text>
    <text x="18" y="104" font-size="14" font-family="sans-serif" fill="#574e3c">沿山步行图 · 虚构样本</text>
  </g>
  <g transform="translate(727 29)" fill="#3e463a"><text y="12" text-anchor="middle" font-size="16" font-family="monospace">N</text><path d="M0 18 9 51 0 43-9 51Z"/><path d="M0 19V43L9 51Z" fill="#d6d3be"/></g>
  <g transform="translate(536 453)"><rect width="224" height="37" fill="#f8f2e4" stroke="#bcb5a0"/><path d="M12 18h34" stroke="#ab4838" stroke-width="4"/><text x="57" y="24" fill="#514c3d" font-size="16" font-family="'PingFang SC',sans-serif">步行线路 · 示意</text></g>
</svg>`;
}

// Local previews are ready before the public repository exists.
if (location.hostname === "raymortwinkle.github.io") {
  document.querySelector("#repository").hidden = false;
}

const preview = document.querySelector("#preview");
const fileName = document.querySelector("#filename");
const source = document.querySelector("#source");
const sourceButton = document.querySelector("#toggle-source");
const download = document.querySelector("#download");
const status = document.querySelector("#sample-status");
let current = "svg";
let sourceVisible = false;
let fileURL;

function markdownPreview(text) {
  const doc = document.implementation.createHTMLDocument("清晨出发");
  const style = doc.createElement("style");
  style.textContent = `*{box-sizing:border-box}body{margin:0;padding:6.4%;color:#344338;background:#f5f1e2;font:clamp(12px,2.95vw,20px)/1.65 "PingFang SC",sans-serif}h1,h2{font-family:"Songti SC",serif;margin:.25em 0}h1{font-size:2em}h2{font-size:1.28em;border-top:1px solid #c7c2ac;padding-top:.6em}p,ul{margin:.5em 0}ul{padding-left:1.4em}`;
  doc.head.append(style);
  let list;
  for (const line of text.split("\n").filter(Boolean)) {
    const match = /^(#{1,2} |- )(.+)$/.exec(line);
    const tag = {"# ": "h1", "## ": "h2", "- ": "li"}[match?.[1]] || "p";
    const element = doc.createElement(tag);
    element.textContent = match?.[2] || line;
    if (tag === "li") {
      if (!list) {
        list = doc.createElement("ul");
        doc.body.append(list);
      }
      list.append(element);
    } else {
      list = undefined;
      doc.body.append(element);
    }
  }
  return "<!doctype html>" + doc.documentElement.outerHTML;
}

function render() {
  const item = samples[current];
  if (fileURL) URL.revokeObjectURL(fileURL);
  fileURL = URL.createObjectURL(new Blob([item.text], {type: item.mime + ";charset=utf-8"}));
  download.href = fileURL;
  download.download = item.file;
  fileName.textContent = item.file;
  if (current === "svg") {
    preview.srcdoc = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><style>*{box-sizing:border-box}body{margin:0;background:#eae8d2}svg{display:block;width:100vw;height:100vh}</style>' + item.text;
  } else {
    preview.srcdoc = current === "html" ? item.text : markdownPreview(item.text);
  }
  source.firstElementChild.textContent = item.text;
  document.querySelectorAll("[data-sample]").forEach(button => {
    button.setAttribute("aria-pressed", String(button.dataset.sample === current));
  });
  setView();
}

function setView() {
  source.hidden = !sourceVisible;
  preview.hidden = sourceVisible;
  sourceButton.textContent = sourceVisible ? "查看预览" : "查看源码";
  sourceButton.setAttribute("aria-pressed", String(sourceVisible));
  status.textContent = `${samples[current].file}，${sourceVisible ? "文件源码" : "文件预览"}。`;
}

document.querySelectorAll("[data-sample]").forEach(button => {
  button.addEventListener("click", () => {
    current = button.dataset.sample;
    render();
  });
});
sourceButton.addEventListener("click", () => {
  sourceVisible = !sourceVisible;
  setView();
});
render();
