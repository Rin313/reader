export const $ = id => document.getElementById(id);
export function listenToggle(obj,key,defaultValue=true){
    obj.checked = getIndexed(key,defaultValue);
    obj.addEventListener("change", () => setIndexed(key, obj.checked));
}
async function _jsonFetch(url,{ headers = {}, body, ...rest } = {}) {
    if ((body && (body.constructor === Object || Array.isArray(body)))) {
        headers['Content-Type'] ??= 'application/json';
        body = JSON.stringify(body);
    }
    const response = await fetch(url, { ...rest, headers, body });
    if (!response.ok) throw Object.assign(new Error(`HTTP ${response.status}`), { status: response.status, data: await response.json().catch(() => undefined)});
    return response.json();//不支持纯文本、blob、204空响应
}
export const get = (url, params, options = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const finalUrl = queryString ? `${url}?${queryString}` : url;
    return _jsonFetch(finalUrl, options);
};
const post = (url, body, options = {}) => _jsonFetch(url, { ...options, method: 'POST', body }); 
const put = (url, body, options = {}) => _jsonFetch(url, { ...options, method: 'PUT', body });
export const uploadAndExtract = (fileObj) => {
    const formData = new FormData();
    // OpenAPI 定义中字段名为 "file"
    formData.append('file', fileObj);

    // 直接传入 formData，_jsonFetch 会跳过 JSON 处理，
    // 浏览器会自动为 fetch 设置 Content-Type: multipart/form-data; boundary=...
    return post(`/upload`, formData);
};

export const segmentSentence = (text) => {
    const payload = {
        text: text
    };
    return post(`/segment`, payload);
};

/*
Args:
        vocab_list: ["run", "book"]
        text_list: ["I am running.", "This is a book."]
        
    Returns:
        List[List[Dict]]: 对应 text_list 中每一行的匹配详情。
        例如:
        [
            [{"start": 5, "length": 7, "matched_text": "running", "vocab_lemma": "run"}],
            [...]
        ]
 */
export const matchVocabulary = (textList) => {
    const payload = {
        text_list: textList
    };
    return post(`/match_vocab`, payload);
};
// return : {"original_text": "string","translated_text": "string"}
export const translate = (text, translator,from_lang,to_lang) => {
    const payload = {
        text: text,
        translator: translator,
        from_lang: from_lang,
        to_lang: to_lang
    };
    return post(`/translate`, payload);
};
/**
 * 批量翻译函数
 * @param {string[]} paragraphs - 文本段落列表
 * @param {string} translator - 翻译器引擎
 * @param {string} from_lang - 源语言
 * @param {string} to_lang - 目标语言
 * @returns {Promise<string[]>} - 翻译后的段落列表，顺序与原列表一致
 */
export const translateParagraphs = async (paragraphs, translator, from_lang, to_lang) => {
    const results = [];
    let currentIndex = 0;

    // 遍历整个段落列表
    while (currentIndex < paragraphs.length) {
        // --- 步骤 1: 构建最大可能的批次 (Batch) ---
        
        // 从当前位置开始，初始化当前批次
        let batch = [paragraphs[currentIndex]];
        let currentBatchLength = paragraphs[currentIndex].length;
        let nextIndex = currentIndex + 1;

        // 向后贪婪匹配，尝试拼接更多段落，直到字数超过 2000
        while (nextIndex < paragraphs.length) {
            const nextPara = paragraphs[nextIndex];
            // 预计算拼接后的长度：当前长度 + 换行符(1) + 下一段长度
            if (currentBatchLength + 1 + nextPara.length > 2000) {
                break; // 超过限制，停止拼接
            }
            
            batch.push(nextPara);
            currentBatchLength += 1 + nextPara.length;
            nextIndex++;
        }

        // --- 步骤 2: 翻译并验证行数 (回溯逻辑) ---
        
        // 如果翻译结果行数不匹配，我们需要不断减少 batch 的大小并重试
        while (batch.length > 0) {
            // 用换行符拼接
            const textPayload = batch.join('\n');

            try {
                // 调用提供的 translate 函数
                const response = await translate(textPayload, translator, from_lang, to_lang);
                
                // 获取翻译结果，处理可能为空的情况
                const translatedText = response.translated_text || "";
                
                // 将结果按换行符分割回列表
                // 注意：使用正则 /\r?\n/ 兼容不同系统可能产生的回车换行
                // 如果翻译结果是空字符串，split会返回[""]，需注意边界情况，但在非空输入下通常不会发生
                let translatedLines = translatedText.split(/\r?\n/);
                
                // 某些特殊情况，如果最后一行是空行，split 可能会多出一个空字符串，视具体需求可进行 trim
                // 这里严格按照题目要求：比较列表长度

                // 检查：翻译后的行数是否等于原始批次的行数
                if (translatedLines.length === batch.length) {
                    // --- 情况 A: 匹配成功 ---
                    results.push(...translatedLines);
                    // 移动主索引，跳过已成功翻译的段落数
                    currentIndex += batch.length;
                    // 跳出重试循环，继续处理剩余段落
                    break; 
                } else {
                    // --- 情况 B: 匹配失败 (行数不一致) ---
                    
                    // 边界保护：如果当前批次只剩1个段落，仍然不匹配（例如翻译器把一句话翻成了两行）
                    // 此时无法继续减少，必须强制接受或报错。为了防止死循环，这里选择强制接受。
                    if (batch.length === 1) {
                        console.warn(`翻译行数不匹配且无法继续缩减 (Index: ${currentIndex})。原句: "${batch[0]}", 译文行数: ${translatedLines.length}`);
                        results.push(...translatedLines); // 此时结果列表长度可能会发生变化，但为了程序健壮性需继续
                        currentIndex += 1;
                        break;
                    }

                    // 核心逻辑：如果不等于原始列表，则减少一个拼接项重新翻译
                    batch.pop();
                    // 循环将回到开头，使用新的（更短的）batch 重新调用 translate
                }
            } catch (error) {
                console.error("翻译请求出错:", error);
                throw error; // 根据业务需求，这里可以选择抛出异常或填入空字符串跳过
            }
        }
    }

    return results;
};
export function moveStrToEnd(list,str,max) {
    const index = list.indexOf(str);
    if (index !== -1) list.splice(index, 1);
    if(max&&list.length>=max)list.splice(0,list.length-max+1);
    list.push(str);
}
export function findSublist(mainList, subList) {
    const subListLength = subList.length;
    for (let i = 0; i <= mainList.length - subListLength; i++) {
        const slice = mainList.slice(i, i + subListLength);
        if (slice.every((item, index) => item === subList[index])) {
            return i;
        }
    }
    return -1;
}
import * as XLSX from 'xlsx';

// 1. 新增：仅读取 Excel 为二维数组
export async function readExcelFile(file) {
  return new Promise(async (resolve, reject) => {
    try {
      const data = await file.arrayBuffer();
      const workbook = XLSX.read(data);
      const firstSheetName = workbook.SheetNames[0];
      if (!firstSheetName) throw new Error('无工作表');
      const worksheet = workbook.Sheets[firstSheetName];
      // header: 1 返回二维数组 [['Title', 'Date'], ['Hello', '2023']]
      const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
      resolve(jsonData);
    } catch (error) {
      reject(error);
    }
  });
}

// 2. 新增：从二维数组中提取指定列（过滤掉非字符串内容，比如标题行）
export function extractColumnFromData(matrixData, columnIndex) {
  // 假设第一行是标题，通常我们希望保留它用于识别，但在生成词库时可能要去掉
  // 这里简单处理：提取所有行，后续由用户确认或自动清洗
  return matrixData.map(row => {
    return row[columnIndex] !== undefined ? row[columnIndex] : null;
  }).filter(item => item && typeof item === 'string' && item.trim() !== '');
}
function openDB() {
  return new Promise((resolve, reject) => {
    // 增加错误处理
    const req = indexedDB.open('kv-db', 1);

    req.onerror = () => reject(new Error(`OpenDB Error: ${req.error?.message}`));

    req.onupgradeneeded = (event) => {
      const db = req.result;
      // 检查是否存在，防止重复创建报错
      if (!db.objectStoreNames.contains('kv')) {
        db.createObjectStore('kv');
      }
    };

    req.onsuccess = () => resolve(req.result);
    
    // 处理版本阻塞情况（例如另一个标签页打开了旧版本）
    req.onblocked = () => reject(new Error('Database blocked: close other tabs'));
  });
}

export async function getIndexed(key, defaultValue) {
  let db;
  try {
    db = await openDB();
    return await new Promise((resolve, reject) => {
      const tx = db.transaction('kv', 'readonly'); // 读操作用 readonly 即可
      const store = tx.objectStore('kv');
      const request = store.get(key);

      // 成功完成事务
      tx.oncomplete = () => {
        resolve(request.result === undefined ? defaultValue : request.result);
      };

      // 处理事务错误（防止卡死）
      tx.onerror = () => reject(new Error(`Get Error: ${tx.error?.message}`));
      tx.onabort = () => reject(new Error('Transaction aborted'));
    });
  } catch (error) {
    console.error(error);
    return defaultValue; // 出错时返回默认值
  } finally {
    if (db) db.close(); // 确保无论成功失败都关闭连接
  }
}

export async function setIndexed(key, obj) {
  let db;
  try {
    db = await openDB();
    await new Promise((resolve, reject) => {
      const tx = db.transaction('kv', 'readwrite');
      const store = tx.objectStore('kv');
      
      try {
        store.put(obj, key);
      } catch (e) {
        // 捕获同步错误（如 key 无效）
        reject(e);
        return;
      }

      tx.oncomplete = () => resolve();
      
      // 处理事务错误（防止卡死）
      tx.onerror = () => reject(new Error(`Set Error: ${tx.error?.message}`));
      tx.onabort = () => reject(new Error('Transaction aborted'));
    });
  } finally {
    if (db) db.close();
  }
}
export const formatTime = (sec) => `00:${Math.floor(sec).toString().padStart(2, '0')}`
const formatVoiceLabel = (voice) => {
  const name = voice.ShortName.split(':')[0].split('-').pop().replace('Neural', '')
  const genderShort = voice.Gender === 'Female' ? 'F' : 'M'
  return `${name} (${genderShort})`
}
export const translatorOptions = [
  { label: 'Google Translate', value: 'google' },
  { label: 'Microsoft Azure', value: 'bing' },
  { label: 'DeepL', value: 'deepl' },
  //{ label: 'DeepL（Unstable）', value: 'deepl' },
  { label: 'Caiyun', value: 'caiyun' },
  { label: 'Alibaba', value: 'alibaba' },
  { label: 'Sogou', value: 'sogou' }
]
export const getAudioUrl = async (abortController,text, voice, rate="+0%") => {
  try {
    const response = await fetch('/tts', { 
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voice: voice, rate }),
      signal: abortController.signal
    })
    if (!response.ok) throw new Error('TTS request failed')
    const audioBlob = await response.blob()
    return URL.createObjectURL(audioBlob)
  } catch (error) {
    if (error.name === 'AbortError') return null
    console.error('TTS Fetch Error:', error)
    throw error
  }
}
export const speedOptions = [0.5,0.75, 1.0, 1.25, 1.5,2,3].map(v => ({ label: `${v}x`, value: v }))
export const formatRate = (rate) => {
  const percent = Math.round((rate - 1) * 100)
  return percent >= 0 ? `+${percent}%` : `${percent}%`
}
export const generateHighlightHtml = (text, matches) => {
  if (!text) return ''
  if (!matches?.length) return text
  const sorted = [...matches].sort((a, b) => b.start - a.start)
  let result = text
  sorted.forEach(m => {
    const { start, length } = m
    if (start < 0 || start + length > result.length) return
    const word = result.slice(start, start + length)
    result = result.slice(0, start) + 
      `<span class="border-b-[1.5px] border-amber-400 text-amber-900/90 cursor-help hover:bg-amber-100/50 hover:text-amber-700 transition-colors">${word}</span>` + 
      result.slice(start + length)
  })
  return result
}
const enVoices = [
    {
      "ShortName": "en-US-AvaMultilingualNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "en-US-AndrewMultilingualNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-AmandaMultilingualNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "en-US-AdamMultilingualNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-EmmaMultilingualNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "en-US-PhoebeMultilingualNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "en-US-AlloyTurboMultilingualNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-EchoTurboMultilingualNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-FableTurboMultilingualNeural",
      "Gender": "Neutral"
    },
    {
      "ShortName": "en-US-OnyxTurboMultilingualNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-NovaTurboMultilingualNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "en-US-ShimmerTurboMultilingualNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "en-US-BrianMultilingualNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-AvaNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "en-US-AndrewNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-EmmaNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "en-US-BrianNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-JennyNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "en-US-GuyNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-AriaNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "en-US-DavisNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-JaneNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "en-US-JasonNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-KaiNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-LunaNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "en-US-SaraNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "en-US-TonyNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-NancyNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "en-US-CoraMultilingualNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "en-US-ChristopherMultilingualNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-BrandonMultilingualNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-AmberNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "en-US-AnaNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "en-US-AshleyNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "en-US-BrandonNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-ChristopherNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-CoraNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "en-US-DavisMultilingualNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-DerekMultilingualNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-DustinMultilingualNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-ElizabethNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "en-US-EricNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-JacobNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-JennyMultilingualNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "en-US-LewisMultilingualNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-LolaMultilingualNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "en-US-MichelleNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "en-US-MonicaNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "en-US-NancyMultilingualNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "en-US-RogerNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-RyanMultilingualNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-SamuelMultilingualNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-SerenaMultilingualNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "en-US-SteffanMultilingualNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "en-US-SteffanNeural",
      "Gender": "Male"
    }
  ];

const cnVoices = [
    {
      "ShortName": "zh-CN-XiaoxiaoNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "zh-CN-YunxiNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "zh-CN-YunjianNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "zh-CN-XiaoyiNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "zh-CN-YunyangNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "zh-CN-XiaochenNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "zh-CN-XiaochenMultilingualNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "zh-CN-XiaohanNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "zh-CN-XiaomengNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "zh-CN-XiaomoNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "zh-CN-XiaoqiuNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "zh-CN-XiaorouNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "zh-CN-XiaoruiNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "zh-CN-XiaoshuangNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "zh-CN-XiaoxiaoDialectsNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "zh-CN-XiaoxiaoMultilingualNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "zh-CN-XiaoyanNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "zh-CN-XiaoyouNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "zh-CN-XiaoyuMultilingualNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "zh-CN-XiaozhenNeural",
      "Gender": "Female"
    },
    {
      "ShortName": "zh-CN-YunfengNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "zh-CN-YunhaoNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "zh-CN-YunjieNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "zh-CN-YunxiaNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "zh-CN-YunxiaoMultilingualNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "zh-CN-YunyeNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "zh-CN-YunyiMultilingualNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "zh-CN-YunzeNeural",
      "Gender": "Male"
    },
    {
      "ShortName": "zh-CN-YunfanMultilingualNeural",
      "Gender": "Male"
    }
  ]  
export const enVoiceOptions = enVoices.map(v => ({ label: formatVoiceLabel(v), value: v.ShortName }))
export const cnVoiceOptions = cnVoices.map(v => ({ label: formatVoiceLabel(v), value: v.ShortName }))
const REFRESH_PARAM = "__sr";

export function smoothRefresh(options) {
  options = options || {};
  const bustCache = options.bustCache !== undefined ? options.bustCache : true;
  const preserveScroll = options.preserveScroll !== undefined ? options.preserveScroll : true;

  // 可选：记录滚动位置
  if (preserveScroll) {
    sessionStorage.setItem("__sr_scrollY", String(window.scrollY));
  }

  const url = new URL(location.href);

  // 关键：让 URL 发生变化以触发一次导航
  url.searchParams.set(REFRESH_PARAM, bustCache ? String(Date.now()) : "1");

  location.assign(url.toString());
}
//页面加载后清理临时参数 + 恢复滚动（可选）//这段在每次加载时跑一下即可（同样不绑定框架）：
// (function cleanupSmoothRefreshParam() {
//   const url = new URL(location.href);
//   if (!url.searchParams.has("__sr")) return;

//   url.searchParams.delete("__sr");
//   history.replaceState(history.state, "", url.toString());

//   const y = Number(sessionStorage.getItem("__sr_scrollY"));
//   sessionStorage.removeItem("__sr_scrollY");

//   if (!Number.isNaN(y)) {
//     requestAnimationFrame(function () {
//       window.scrollTo(0, y);
//     });
//   }
// })();
export async function getItem(key,defaultValue) {
    const value=await get(`/api/storage/${key}`);
    return value?value:defaultValue;
}
export async function setItem(key, value) {
    return put(`/api/storage/${key}`,value);
}