import { reduceTalkStyle } from "@/utils/reduceTalkStyle";
import { koeiromapV0 } from "../koeiromap/koeiromap";
import { TalkStyle } from "../messages/messages";

export async function synthesizeVoice(
  message: string,
  speakerX: number,
  speakerY: number,
  style: TalkStyle
) {
  const koeiroRes = await koeiromapV0(message, speakerX, speakerY, style);
  return { audio: koeiroRes.audio };
}

export async function synthesizeVoiceApi(
  message: string,
  speakerX: number,
  speakerY: number,
  style: TalkStyle,
  apiKey: string
) {
  // Free向けに感情を制限する
  const reducedStyle = reduceTalkStyle(style);

  const payload = {
    target_text_content: message, // 新接口的请求数据格式
  };

  const headers = {
    "Content-Type": "application/json",
  };

  // 发送请求到新的后端接口
  const url = "http://192.10.221.53:30004/run-inference";  // 你的Python后端接口URL
  const res = await fetch(url, {
    method: "POST",
    headers: headers,
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error("Failed to fetch TTS audio from the server");
  }

  // 获取返回的音频文件内容（二进制数据）
  const audioBlob = await res.blob();

  // 将返回的音频 Blob 转换为 ArrayBuffer
  const audioBuffer = await audioBlob.arrayBuffer();

  // 返回音频的 ArrayBuffer 数据
  return { audio: audioBuffer };
}


// export async function synthesizeVoiceApi(
//   message: string,
//   speakerX: number,
//   speakerY: number,
//   style: TalkStyle,
//   apiKey: string
// ) {
//   // Free向けに感情を制限する
//   const reducedStyle = reduceTalkStyle(style);

//   const body = {
//     message: message,
//     speakerX: speakerX,
//     speakerY: speakerY,
//     style: reducedStyle,
//     apiKey: apiKey,
//   };

//   const res = await fetch("/api/tts", {
//     method: "POST",
//     headers: {
//       "Content-Type": "application/json",
//     },
//     body: JSON.stringify(body),
//   });
//   const data = (await res.json()) as any;

//   return { audio: data.audio };
// }
