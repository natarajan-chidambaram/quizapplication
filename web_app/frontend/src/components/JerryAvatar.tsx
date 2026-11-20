import React from "react";

interface JerryAvatarProps {
  /** True while Jerry claps (correct answer in Learning Mode). */
  clapping?: boolean;
  size?: number;
}

/**
 * Cheerful Jerry avatar in the style of Jerry from the Tom & Jerry cartoon:
 * warm orange-brown fur, oversized round ears with peachy-pink insides, a
 * little hair tuft, big expressive eyes, tiny black nose, buck-tooth grin,
 * whiskers, cream muzzle/belly and a long curvy tail. When `clapping` is
 * true he bounces with joy and his paws clap together (Learning Mode).
 */
const JerryAvatar: React.FC<JerryAvatarProps> = ({ clapping = false, size = 96 }) => (
  <div
    className={`jerry-avatar${clapping ? " jerry-avatar--cheer" : ""}`}
    role="img"
    aria-label={clapping ? "Jerry the mouse clapping and cheering" : "Jerry the mouse"}
  >
    <svg viewBox="0 0 120 120" width={size} height={size} aria-hidden="true" focusable="false">
      {/* long curvy tail */}
      <path
        d="M80 100 Q 104 104 102 84 Q 100 68 88 72"
        fill="none"
        stroke="#8a4f1c"
        strokeWidth="4"
        strokeLinecap="round"
      />
      {/* big round ears with peachy-pink insides */}
      <circle cx="28" cy="28" r="18" fill="#c17a2e" stroke="#8a4f1c" strokeWidth="2" />
      <circle cx="28" cy="28" r="9.5" fill="#f9cfa3" />
      <circle cx="92" cy="28" r="18" fill="#c17a2e" stroke="#8a4f1c" strokeWidth="2" />
      <circle cx="92" cy="28" r="9.5" fill="#f9cfa3" />
      {/* hair tuft on top */}
      <path
        d="M50 16 Q 54 4 60 14 Q 65 3 70 14 Q 75 5 78 17 Q 69 12 60 15 Q 51 12 50 16 Z"
        fill="#8a4f1c"
      />
      {/* head */}
      <ellipse cx="60" cy="44" rx="33" ry="29" fill="#c17a2e" />
      {/* cream muzzle */}
      <ellipse cx="60" cy="57" rx="22" ry="17" fill="#f9d8ae" />
      {/* big expressive eyes */}
      <ellipse cx="48" cy="37" rx="9" ry="11" fill="#ffffff" stroke="#8a4f1c" strokeWidth="1.4" />
      <ellipse cx="72" cy="37" rx="9" ry="11" fill="#ffffff" stroke="#8a4f1c" strokeWidth="1.4" />
      <circle cx="49.5" cy="39.5" r="4" fill="#241207" />
      <circle cx="73.5" cy="39.5" r="4" fill="#241207" />
      <circle cx="51" cy="37.8" r="1.4" fill="#ffffff" />
      <circle cx="75" cy="37.8" r="1.4" fill="#ffffff" />
      {/* happy eyebrows */}
      <path d="M40 24 Q 48 21 55 24" fill="none" stroke="#8a4f1c" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M65 24 Q 72 21 80 24" fill="none" stroke="#8a4f1c" strokeWidth="1.6" strokeLinecap="round" />
      {/* tiny black nose */}
      <ellipse cx="60" cy="51" rx="4.2" ry="3.2" fill="#241207" />
      <circle cx="61.4" cy="50" r="1" fill="#ffffff" opacity="0.85" />
      {/* buck-tooth grin */}
      <path d="M48 59 Q 60 68 72 59" fill="none" stroke="#7a451a" strokeWidth="2" strokeLinecap="round" />
      <rect x="56.5" y="62.5" width="7" height="7" rx="1.5" fill="#ffffff" stroke="#7a451a" strokeWidth="1.2" />
      <line x1="60" y1="62.8" x2="60" y2="69.2" stroke="#7a451a" strokeWidth="1" />
      {/* whiskers */}
      <g stroke="#7a451a" strokeWidth="1.1" strokeLinecap="round" opacity="0.9">
        <line x1="22" y1="55" x2="38" y2="57" />
        <line x1="22" y1="60" x2="38" y2="60" />
        <line x1="23" y1="65" x2="38" y2="63" />
        <line x1="82" y1="57" x2="98" y2="55" />
        <line x1="82" y1="60" x2="98" y2="60" />
        <line x1="82" y1="63" x2="97" y2="65" />
      </g>
      {/* body and cream belly */}
      <ellipse cx="60" cy="94" rx="23" ry="18" fill="#c17a2e" />
      <ellipse cx="60" cy="96" rx="14" ry="11.5" fill="#f9d8ae" />
      {/* clapping paws */}
      <g className="jerry-hand jerry-hand--left">
        <circle cx="42" cy="90" r="7" fill="#f9d8ae" stroke="#8a4f1c" strokeWidth="1.6" />
        <circle cx="40" cy="88" r="1.2" fill="#e8a76f" />
      </g>
      <g className="jerry-hand jerry-hand--right">
        <circle cx="78" cy="90" r="7" fill="#f9d8ae" stroke="#8a4f1c" strokeWidth="1.6" />
        <circle cx="80" cy="88" r="1.2" fill="#e8a76f" />
      </g>
      {/* feet */}
      <ellipse cx="49" cy="110" rx="9" ry="5" fill="#f9d8ae" stroke="#8a4f1c" strokeWidth="1.4" />
      <ellipse cx="71" cy="110" rx="9" ry="5" fill="#f9d8ae" stroke="#8a4f1c" strokeWidth="1.4" />
    </svg>
  </div>
);

export default JerryAvatar;
