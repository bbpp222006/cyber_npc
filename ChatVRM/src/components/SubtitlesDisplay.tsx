import React from "react";
import styles from "@/styles/SubtitlesDisplay.module.css";

interface SubtitlesDisplayProps {
  subtitle: string;
}

const SubtitlesDisplay: React.FC<SubtitlesDisplayProps> = ({ subtitle }) => {
  return (
    <div className={styles.subtitleContainer}>
      <p className={styles.subtitle}>{subtitle}</p>
    </div>
  );
};

export default SubtitlesDisplay;
