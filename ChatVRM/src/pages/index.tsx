import { useCallback, useContext, useEffect, useRef, useState } from "react";
import VrmViewer from "@/components/vrmViewer";
import { ViewerContext } from "@/features/vrmViewer/viewerContext";
import {
  Message,
  textsToScreenplay,
  Screenplay,
} from "@/features/messages/messages";
import { speakCharacter } from "@/features/messages/speakCharacter";
import { SYSTEM_PROMPT } from "@/features/constants/systemPromptConstants";
import { KoeiroParam, DEFAULT_PARAM } from "@/features/constants/koeiroParam";
import { getChatResponseStream } from "@/features/chat/openAiChat";
import { Introduction } from "@/components/introduction";
import { Menu } from "@/components/menu";
import { GitHubLink } from "@/components/githubLink";
import { Meta } from "@/components/meta";

export default function Home() {
  const { viewer } = useContext(ViewerContext);

  const [systemPrompt, setSystemPrompt] = useState(SYSTEM_PROMPT);
  const [openAiKey, setOpenAiKey] = useState("aaa");
  const [koeiromapKey, setKoeiromapKey] = useState("");
  const [koeiroParam, setKoeiroParam] = useState<KoeiroParam>(DEFAULT_PARAM);
  const [chatProcessing, setChatProcessing] = useState(false);
  const [chatLog, setChatLog] = useState<Message[]>([]);
  const [assistantMessage, setAssistantMessage] = useState("");

  // 使用useRef来保持WebSocket实例和重连次数的引用
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 10; // 最大重连次数
  const reconnectDelay = 2000; // 初始重连延迟（毫秒）

  // 从本地存储中加载参数
  useEffect(() => {
    if (window.localStorage.getItem("chatVRMParams")) {
      const params = JSON.parse(
        window.localStorage.getItem("chatVRMParams") as string
      );
      setSystemPrompt(params.systemPrompt ?? SYSTEM_PROMPT);
      setKoeiroParam(params.koeiroParam ?? DEFAULT_PARAM);
      setChatLog(params.chatLog ?? []);
    }
  }, []);

  // 将参数保存到本地存储
  useEffect(() => {
    process.nextTick(() =>
      window.localStorage.setItem(
        "chatVRMParams",
        JSON.stringify({ systemPrompt, koeiroParam, chatLog })
      )
    );
  }, [systemPrompt, koeiroParam, chatLog]);

  // 处理聊天记录的更改
  const handleChangeChatLog = useCallback(
    (targetIndex: number, text: string) => {
      const newChatLog = chatLog.map((v: Message, i) => {
        return i === targetIndex ? { role: v.role, content: text } : v;
      });

      setChatLog(newChatLog);
    },
    [chatLog]
  );

  /**
   * 按句子顺序请求并播放语音
   */
  const handleSpeakAi = useCallback(
    async (
      screenplay: Screenplay,
      onStart?: () => void,
      onEnd?: () => void
    ) => {
      speakCharacter(screenplay, viewer, koeiromapKey, onStart, onEnd);
    },
    [viewer, koeiromapKey]
  );

  /**
   * 与助手进行对话
   */
  const handleSendChat = useCallback(
    async (text: string) => {
      if (!openAiKey) {
        setAssistantMessage("API密钥未输入");
        return;
      }

      const newMessage = text;

      if (newMessage == null) return;

      setChatProcessing(true);
      // 添加用户的发言并显示
      const messageLog: Message[] = [
        ...chatLog,
        { role: "user", content: newMessage },
      ];
      setChatLog(messageLog);

      // 发送到 Chat GPT
      const messages: Message[] = [
        {
          role: "system",
          content: systemPrompt,
        },
        ...messageLog,
      ];

      const stream = await getChatResponseStream(messages, openAiKey).catch(
        (e) => {
          console.error(e);
          return null;
        }
      );
      if (stream == null) {
        setChatProcessing(false);
        return;
      }

      const reader = stream.getReader();
      let receivedMessage = "";
      let aiTextLog = "";
      let tag = "";
      const sentences = new Array<string>();
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          receivedMessage += value;
          console.log("接收到的数据块:", value); // 输出当前接收到的数据块

          // 检测回复内容的标签部分
          const tagMatch = receivedMessage.match(/^\[(.*?)\]/);
          if (tagMatch && tagMatch[0]) {
            tag = tagMatch[0];
            receivedMessage = receivedMessage.slice(tag.length);
            console.log("提取到的标签:", tag); // 输出提取到的标签
          }

          // 按句子单位切割回复内容并处理
          const sentenceMatch = receivedMessage.match(
            /^(.+[。．！？\n]|.{10,}[、,])/
          );
          if (sentenceMatch && sentenceMatch[0]) {
            const sentence = sentenceMatch[0];
            sentences.push(sentence);
            receivedMessage = receivedMessage
              .slice(sentence.length)
              .trimStart();

            console.log("提取的句子:", sentence); // 输出提取到的句子

            // 判断是否为不需要的字符串
            if (
              !sentence.replace(
                /^[\s\[\(\{「［（【『〈《〔｛«‹〘〚〛〙›»〕》〉』】）］」\}\)\]]+$/g,
                ""
              )
            ) {
              console.log("跳过不必要的句子:", sentence); // 输出跳过的句子
              continue;
            }

            const aiText = `${tag} ${sentence}`;
            const aiTalks = textsToScreenplay([aiText], koeiroParam);
            aiTextLog += aiText;

            console.log("生成的AI文本:", aiText); // 输出生成的 AI 文本

            // 按句子生成语音并播放，同时显示回复
            const currentAssistantMessage = sentences.join(" ");
            console.log("当前助手的消息:", currentAssistantMessage); // 输出当前助手的消息

            handleSpeakAi(aiTalks[0], () => {
              setAssistantMessage(currentAssistantMessage);
            });
          }
        }
      } catch (e) {
        setChatProcessing(false);
        console.error("语音处理过程中出错:", e); // 输出错误信息
      } finally {
        reader.releaseLock();
        console.log("释放读取器锁."); // 输出释放锁的日志
      }

      // 将助手的回复添加到日志中
      const messageLogAssistant: Message[] = [
        ...messageLog,
        { role: "assistant", content: aiTextLog },
      ];

      setChatLog(messageLogAssistant);
      setChatProcessing(false);
    },
    [systemPrompt, chatLog, handleSpeakAi, openAiKey, koeiroParam]
  );

  /**
   * 建立WebSocket连接并处理自动重连
   */
  useEffect(() => {
    let isMounted = true; // 标记组件是否仍然挂载
    let reconnectTimeout: NodeJS.Timeout;

    const connectWebSocket = () => {
      if (!isMounted) return;

      const ws = new WebSocket("ws://192.168.123.235:38024/ws");
      wsRef.current = ws;

      ws.binaryType = "arraybuffer";

      ws.onopen = () => {
        console.log("WebSocket连接已建立。");
        // 重置重连次数
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        if (typeof event.data === "string") {
          try {
            const message = JSON.parse(event.data);
            const { type, content, data } = message;

            switch (type) {
              case "user_input":
                console.log("接收到用户输入:", content);
                handleSendChat(content);
                break;
              case "text":
                console.log("接收到文本消息:", content);
                // setChatLog((prevChatLog) => [
                //   ...prevChatLog,
                //   { role: "assistant", content },
                // ]);
                setAssistantMessage(content);
                break;
              case "text_audio":
                console.log("接收到文本和音频消息:", content);
                // setChatLog((prevChatLog) => [
                //   ...prevChatLog,
                //   { role: "assistant", content },
                // ]);
                setAssistantMessage(content);
                if (data) {
                  // 假设音频数据是base64编码的字符串
                  const audioBlob = base64ToBlob(data, "audio/mp3");
                  const audioUrl = URL.createObjectURL(audioBlob);
                  const audio = new Audio(audioUrl);
                  audio.play().catch((error) =>
                    console.error("音频播放失败:", error)
                  );
                }
                break;
              default:
                console.warn("未知的消息类型:", type);
            }
          } catch (e) {
            console.error("解析JSON消息时出错:", e);
          }
        } else if (event.data instanceof ArrayBuffer) {
          // 处理纯二进制消息（如果需要）
          console.log("接收到二进制消息");
          const audioBlob = new Blob([event.data], { type: "audio/mp3" });
          const audioUrl = URL.createObjectURL(audioBlob);
          const audio = new Audio(audioUrl);
          audio.play().catch((error) =>
            console.error("音频播放失败:", error)
          );
        }
      };

      ws.onerror = (error) => {
        console.error("WebSocket错误:", error);
      };

      ws.onclose = (event) => {
        console.log("WebSocket连接已关闭:", event);
        // 尝试重连
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = reconnectDelay;
          console.log(`尝试在 ${delay} 毫秒后重连...`);
          reconnectTimeout = setTimeout(() => {
            reconnectAttemptsRef.current += 1;
            connectWebSocket();
          }, delay);
        } else {
          console.error("已达到最大重连次数，停止重连。");
        }
      };
    };

    connectWebSocket();

    // 清理函数，在组件卸载时关闭WebSocket连接并清除定时器
    return () => {
      isMounted = false;
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
    };
  }, []);

  /**
   * 将base64字符串转换为Blob对象
   * @param base64
   * @param mime
   * @returns Blob
   */
  const base64ToBlob = (base64: string, mime: string) => {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: mime });
  };


  return (
    <div className={"font-M_PLUS_2"}>
      <Meta />
      {/* <Introduction
        openAiKey={openAiKey}
        koeiroMapKey={koeiromapKey}
        onChangeAiKey={setOpenAiKey}
        onChangeKoeiromapKey={setKoeiromapKey}
      /> */}
      <VrmViewer />
      {/* 移除MessageInputContainer，因为我们使用WebSocket来接收输入 */}
      <Menu
        openAiKey={openAiKey}
        systemPrompt={systemPrompt}
        chatLog={chatLog}
        koeiroParam={koeiroParam}
        assistantMessage={assistantMessage}
        koeiromapKey={koeiromapKey}
        onChangeAiKey={setOpenAiKey}
        onChangeSystemPrompt={setSystemPrompt}
        onChangeChatLog={handleChangeChatLog}
        onChangeKoeiromapParam={setKoeiroParam}
        handleClickResetChatLog={() => setChatLog([])}
        handleClickResetSystemPrompt={() => setSystemPrompt(SYSTEM_PROMPT)}
        onChangeKoeiromapKey={setKoeiromapKey}
      />
      <GitHubLink />
    </div>
  );
}
