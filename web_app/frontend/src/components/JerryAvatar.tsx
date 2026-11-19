import React from "react";

interface JerryAvatarProps {
  /** True while Jerry claps (correct answer in Learning Mode). */
  clapping?: boolean;
  size?: number;
}

/**
 * Cheerful Jerry avatar in the style of the Tom and Jerry cartoon,
 * drawn as inline SVG so it actually resembles the character: a brown
 * mouse with big round ears (tan insides), a tan muzzle, buck tooth
 * smile, red bow tie, long tail and little tan hands. When `clapping`
 * is true his hands clap together and he bounces with joy
 * (request update #1 / R20).
 */
const JerryAvatar: React.FC<JerryAvatarProps> = ({ clapping = false, size = 96 }) => (
  <div
    className={`jerry-avatar${clapping ? " jerry-avatar--cheer" : ""}`}
    role="img"
    aria-label={clapping ? "Jerry the mouse clapping and cheering" : "Jerry the mouse"}
  >
    <svg viewBox="0 0 100 100" width={size} height={size} aria-hidden="true" focusable="false">
      {/* long curvy tail */}
      <path
        d="M67 82 Q 88 88 87 70 Q 86 58 75 59"
        fill="none"
        stroke="#a9662c"
        strokeWidth="4"
        strokeLinecap="round"
      />
      {/* big round ears with tan insides */}
      <circle cx="26" cy="26" r="15" fill="#b06f2e" />
      <circle cx="26" cy="26" r="8" fill="#f2c896" />
      <circle cx="74" cy="26" r="15" fill="#b06f2e" />
      <circle cx="74" cy="26" r="8" fill="#f2c896" />
      {/* head */}
      <ellipse cx="50" cy="38" rx="27" ry="24" fill="#b06f2e" />
      {/* tan muzzle */}
      <ellipse cx="50" cy="47" rx="17" ry="13" fill="#f2c896" />
      {/* eyes */}
      <ellipse cx="41" cy="31" rx="6.5" ry="7.5" fill="#ffffff" stroke="#7a4a1d" strokeWidth="1" />
      <ellipse cx="59" cy="31" rx="6.5" ry="7.5" fill="#ffffff" stroke="#7a4a1d" strokeWidth="1" />
      <circle cx="42.5" cy="33" r="2.6" fill="#3b2314" />
      <circle cx="60.5" cy="33" r="2.6" fill="#3b2314" />
      <circle cx="43.4" cy="32" r="0.9" fill="#ffffff" />
      <circle cx="61.4" cy="32" r="0.9" fill="#ffffff" />
      {/* nose */}
      <ellipse cx="50" cy="42" rx="3" ry="2.4" fill="#7a4a1d" />
      {/* cheerful smile */}
      <path d="M41 49 Q 50 56 59 49" fill="none" stroke="#7a4a1d" strokeWidth="2" strokeLinecap="round" />
      {/* body and tan belly */}
      <ellipse cx="50" cy="76" rx="19" ry="15" fill="#b06f2e" />
      <ellipse cx="50" cy="78" rx="12" ry="10" fill="#f2c896" />
      {/* red bow tie */}
      <path d="M44 61 L50 64 L44 67 Z" fill="#e03131" />
      <path d="M56 61 L50 64 L56 67 Z" fill="#e03131" />
      <circle cx="50" cy="64" r="1.8" fill="#b02525" />
      {/* clapping hands */}
      <g className="jerry-hand jerry-hand--left">
        <circle cx="36" cy="72" r="6" fill="#f2c896" stroke="#b06f2e" strokeWidth="1.5" />
      </g>
      <g className="jerry-hand jerry-hand--right">
        <circle cx="64" cy="72" r="6" fill="#f2c896" stroke="#b06f2e" strokeWidth="1.5" />
      </g>
      {/* feet */}
      <ellipse cx="41" cy="90" rx="7" ry="4" fill="#f2c896" />
      <ellipse cx="59" cy="90" rx="7" ry="4" fill="#f2c896" />
    </svg>
  </div>
);

export default JerryAvatar;
