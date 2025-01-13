import { useEffect, useState, useRef } from "react";
import SubtitlesDisplay from "@/components/SubtitlesDisplay";
import styles from "@/styles/SubtitlesPage.module.css";

const SubtitlesPage = () => {
  const [subtitle, setSubtitle] = useState<string>("");
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);
  const maxReconnectAttempts = 5;
  const reconnectDelayRef = useRef<number>(1000); // Start with 1 second

  useEffect(() => {
    let reconnectTimeout: NodeJS.Timeout;

    const connect = () => {
      wsRef.current = new WebSocket("ws://192.168.123.235:38024/ws");

      wsRef.current.onopen = () => {
        console.log("字幕页面 WebSocket 连接已建立。");
        // Reset reconnection attempts on successful connection
        reconnectAttemptsRef.current = 0;
        reconnectDelayRef.current = 1000; // Reset to initial delay
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === "text_audio") {
            const { content } = message;
            if (typeof content === "object" && content !== null) {
              const { tag, text } = content;
              setSubtitle(`${tag} ${text}`);
            } else if (typeof content === "string") {
              setSubtitle(content);
            }
          }
        } catch (error) {
          console.error("解析 WebSocket 消息时出错:", error);
        }
      };

      wsRef.current.onerror = (error) => {
        console.error("字幕页面 WebSocket 错误:", error);
      };

      wsRef.current.onclose = (event) => {
        console.log("字幕页面 WebSocket 连接已关闭:", event);
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = reconnectDelayRef.current;
          console.log(`尝试在 ${delay / 1000} 秒后重新连接...`);
          reconnectTimeout = setTimeout(() => {
            reconnectAttemptsRef.current += 1;
            reconnectDelayRef.current = Math.min(reconnectDelayRef.current * 2, 30000); // Exponential backoff up to 30 seconds
            connect();
          }, delay);
        } else {
          console.error("达到最大重连次数，停止重连。");
        }
      };
    };

    connect();

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  return (
    <div className={styles.container}>
      <SubtitlesDisplay subtitle={subtitle} />
    </div>
  );
};

export default SubtitlesPage;
