"use client";

import { SignInButton, SignUpButton, useAuth } from "@clerk/nextjs";
import Link from "next/link";
import Image from "next/image";
import { useEffect, useState } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { CyberButton } from "@/components/cyber/button";
import { Zap } from "lucide-react";

/* ─── Config ─── */
const INTRO_DURATION = 2800; // ms
const GLITCH_FRAGMENTS = [
  "INITIALIZING...",
  "NEURAL LINK",
  "SYSTEM BOOT",
  "AGENT SYNC",
  "LOADING CORE",
  "CALIBRATING",
  "ONLINE",
];
const ease = [0.16, 1, 0.3, 1] as [number, number, number, number];

/* ─── Seeded pseudo-random (deterministic on server + client) ─── */
function seededRandom(seed: number) {
  const x = Math.sin(seed * 9301 + 49297) * 233280;
  return x - Math.floor(x);
}

/* ─── Glitch Block ─── */
const GLITCH_COLORS = ["#00ff88", "#ff00ff", "#00d4ff", "#ff3366", "#ffcc00"];

/* Pre-compute all glitch block styles at module level (runs once, same on server + client) */
const GLITCH_BLOCKS = Array.from({ length: 18 }, (_, i) => ({
  left: `${Math.round(seededRandom(i * 4 + 1) * 10000) / 100}%`,
  top: `${Math.round(seededRandom(i * 4 + 2) * 10000) / 100}%`,
  width: `${Math.round(30 + seededRandom(i * 4 + 3) * 200)}px`,
  height: `${Math.round(2 + seededRandom(i * 4 + 4) * 20)}px`,
  backgroundColor: GLITCH_COLORS[i % GLITCH_COLORS.length],
  repeatDelay: Math.round(seededRandom(i * 4 + 5) * 400) / 1000,
}));

function GlitchBlock({ delay, index }: { delay: number; index: number }) {
  const b = GLITCH_BLOCKS[index];

  return (
    <motion.div
      className="absolute pointer-events-none"
      style={{
        left: b.left,
        top: b.top,
        width: b.width,
        height: b.height,
        backgroundColor: b.backgroundColor,
        mixBlendMode: "screen" as const,
        opacity: 0,
      }}
      animate={{
        opacity: [0, 0.8, 0.8, 0],
        scaleX: [1, 1.5, 0.8, 1],
      }}
      transition={{
        duration: 0.15,
        delay,
        repeat: 3,
        repeatDelay: b.repeatDelay,
      }}
    />
  );
}

/* ─── Glitch Intro Overlay ─── */
function GlitchIntro({ onComplete }: { onComplete: () => void }) {
  const [textIdx, setTextIdx] = useState(0);

  useEffect(() => {
    const timer = setTimeout(onComplete, INTRO_DURATION);
    const textTimer = setInterval(() => {
      setTextIdx((i) => (i + 1) % GLITCH_FRAGMENTS.length);
    }, 280);
    return () => {
      clearTimeout(timer);
      clearInterval(textTimer);
    };
  }, [onComplete]);

  return (
    <motion.div
      className="fixed inset-0 z-[100] bg-[#0a0a0f] overflow-hidden"
      exit={{
        opacity: 0,
        filter: "brightness(3) blur(8px)",
        transition: { duration: 0.4, ease },
      }}
    >
      {/* Flickering hero image 1 — robotic hand */}
      <motion.div
        className="absolute inset-0"
        animate={{
          opacity: [0, 0, 0.4, 0, 0.3, 0, 0.5, 0, 0],
          filter: [
            "hue-rotate(0deg) saturate(2)",
            "hue-rotate(90deg) saturate(3)",
            "hue-rotate(180deg) saturate(2)",
            "hue-rotate(270deg) saturate(3)",
            "hue-rotate(0deg) saturate(2)",
          ],
        }}
        transition={{ duration: 2.5, ease: "linear" }}
      >
        <Image
          src="/hero-1.jpg"
          alt=""
          fill
          sizes="100vw"
          className="object-cover"
          style={{ mixBlendMode: "screen" }}
          priority
        />
      </motion.div>

      {/* Flickering hero image 2 — glitched portrait */}
      <motion.div
        className="absolute inset-0"
        animate={{
          opacity: [0, 0.5, 0, 0, 0.4, 0, 0, 0.6, 0],
          filter: [
            "hue-rotate(180deg) saturate(2)",
            "hue-rotate(90deg) saturate(3)",
            "hue-rotate(0deg) saturate(2)",
            "hue-rotate(270deg) saturate(3)",
            "hue-rotate(180deg) saturate(2)",
          ],
        }}
        transition={{ duration: 2.5, ease: "linear", delay: 0.15 }}
      >
        <Image
          src="/hero-2.jpg"
          alt=""
          fill
          sizes="100vw"
          className="object-cover"
          style={{ mixBlendMode: "screen" }}
          priority
        />
      </motion.div>

      {/* Flickering hero image 3 — network collage */}
      <motion.div
        className="absolute inset-0"
        animate={{
          opacity: [0, 0, 0, 0.5, 0, 0.3, 0, 0, 0],
          filter: [
            "hue-rotate(270deg) saturate(2.5)",
            "hue-rotate(180deg) saturate(2)",
            "hue-rotate(90deg) saturate(3)",
            "hue-rotate(0deg) saturate(2)",
            "hue-rotate(270deg) saturate(2.5)",
          ],
        }}
        transition={{ duration: 2.5, ease: "linear", delay: 0.35 }}
      >
        <Image
          src="/hero-3.jpg"
          alt=""
          fill
          sizes="100vw"
          className="object-cover"
          style={{ mixBlendMode: "screen" }}
        />
      </motion.div>

      {/* Flickering hero image 4 — digital escape */}
      <motion.div
        className="absolute inset-0"
        animate={{
          opacity: [0, 0, 0.45, 0, 0, 0, 0.35, 0, 0],
          filter: [
            "hue-rotate(120deg) saturate(2)",
            "hue-rotate(240deg) saturate(3)",
            "hue-rotate(0deg) saturate(2)",
            "hue-rotate(60deg) saturate(2.5)",
            "hue-rotate(120deg) saturate(2)",
          ],
        }}
        transition={{ duration: 2.5, ease: "linear", delay: 0.55 }}
      >
        <Image
          src="/hero-4.jpg"
          alt=""
          fill
          sizes="100vw"
          className="object-cover"
          style={{ mixBlendMode: "screen" }}
        />
      </motion.div>

      {/* Flickering hero image 5 — vaporwave */}
      <motion.div
        className="absolute inset-0"
        animate={{
          opacity: [0, 0.3, 0, 0, 0, 0.4, 0, 0, 0],
          filter: [
            "hue-rotate(30deg) saturate(2)",
            "hue-rotate(150deg) saturate(3)",
            "hue-rotate(270deg) saturate(2)",
            "hue-rotate(330deg) saturate(2.5)",
            "hue-rotate(30deg) saturate(2)",
          ],
        }}
        transition={{ duration: 2.5, ease: "linear", delay: 0.7 }}
      >
        <Image
          src="/hero-5.jpg"
          alt=""
          fill
          sizes="100vw"
          className="object-cover"
          style={{ mixBlendMode: "screen" }}
        />
      </motion.div>

      {/* Flickering hero image 6 — black hole */}
      <motion.div
        className="absolute inset-0"
        animate={{
          opacity: [0, 0, 0, 0, 0.5, 0, 0, 0.3, 0],
          filter: [
            "hue-rotate(160deg) saturate(2) brightness(1.5)",
            "hue-rotate(200deg) saturate(3) brightness(1.3)",
            "hue-rotate(120deg) saturate(2) brightness(1.4)",
            "hue-rotate(240deg) saturate(2.5) brightness(1.5)",
            "hue-rotate(160deg) saturate(2) brightness(1.5)",
          ],
        }}
        transition={{ duration: 2.5, ease: "linear", delay: 0.9 }}
      >
        <Image
          src="/hero-6.jpg"
          alt=""
          fill
          sizes="100vw"
          className="object-cover"
          style={{ mixBlendMode: "screen" }}
        />
      </motion.div>

      {/* Flickering hero image 7 — retro control room */}
      <motion.div
        className="absolute inset-0"
        animate={{
          opacity: [0, 0.4, 0, 0, 0, 0.35, 0, 0, 0],
          filter: [
            "hue-rotate(40deg) saturate(2)",
            "hue-rotate(160deg) saturate(3)",
            "hue-rotate(280deg) saturate(2)",
            "hue-rotate(80deg) saturate(2.5)",
            "hue-rotate(40deg) saturate(2)",
          ],
        }}
        transition={{ duration: 2.5, ease: "linear", delay: 1.05 }}
      >
        <Image
          src="/hero-7.jpg"
          alt=""
          fill
          sizes="100vw"
          className="object-cover"
          style={{ mixBlendMode: "screen" }}
        />
      </motion.div>

      {/* Flickering hero image 8 — night city neon */}
      <motion.div
        className="absolute inset-0"
        animate={{
          opacity: [0, 0, 0.3, 0, 0.45, 0, 0, 0, 0],
          filter: [
            "hue-rotate(200deg) saturate(2) brightness(1.3)",
            "hue-rotate(320deg) saturate(3) brightness(1.2)",
            "hue-rotate(80deg) saturate(2) brightness(1.3)",
            "hue-rotate(140deg) saturate(2.5) brightness(1.3)",
            "hue-rotate(200deg) saturate(2) brightness(1.3)",
          ],
        }}
        transition={{ duration: 2.5, ease: "linear", delay: 1.2 }}
      >
        <Image
          src="/hero-8.jpg"
          alt=""
          fill
          sizes="100vw"
          className="object-cover"
          style={{ mixBlendMode: "screen" }}
        />
      </motion.div>

      {/* Flickering hero image 9 — awaken the world */}
      <motion.div
        className="absolute inset-0"
        animate={{
          opacity: [0, 0, 0, 0.4, 0, 0, 0.3, 0, 0],
          filter: [
            "hue-rotate(100deg) saturate(2.5)",
            "hue-rotate(220deg) saturate(2)",
            "hue-rotate(340deg) saturate(3)",
            "hue-rotate(50deg) saturate(2)",
            "hue-rotate(100deg) saturate(2.5)",
          ],
        }}
        transition={{ duration: 2.5, ease: "linear", delay: 1.35 }}
      >
        <Image
          src="/hero-9.jpg"
          alt=""
          fill
          sizes="100vw"
          className="object-cover"
          style={{ mixBlendMode: "screen" }}
        />
      </motion.div>

      {/* Flickering hero image 10 — aerial city lights */}
      <motion.div
        className="absolute inset-0"
        animate={{
          opacity: [0, 0.35, 0, 0, 0, 0, 0.4, 0, 0],
          filter: [
            "hue-rotate(250deg) saturate(2) brightness(1.2)",
            "hue-rotate(10deg) saturate(3) brightness(1.1)",
            "hue-rotate(130deg) saturate(2) brightness(1.2)",
            "hue-rotate(300deg) saturate(2.5) brightness(1.2)",
            "hue-rotate(250deg) saturate(2) brightness(1.2)",
          ],
        }}
        transition={{ duration: 2.5, ease: "linear", delay: 1.5 }}
      >
        <Image
          src="/hero-10.jpg"
          alt=""
          fill
          sizes="100vw"
          className="object-cover"
          style={{ mixBlendMode: "screen" }}
        />
      </motion.div>

      {/* Scan lines sweep */}
      <motion.div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,255,136,0.03) 2px, rgba(0,255,136,0.03) 4px)",
        }}
        animate={{ y: ["-100%", "100%"] }}
        transition={{ duration: 1.5, repeat: 2, ease: "linear" }}
      />

      {/* Glitch blocks */}
      {Array.from({ length: 18 }, (_, i) => (
        <GlitchBlock key={i} delay={i * 0.12} index={i} />
      ))}

      {/* Center text fragments */}
      <div className="absolute inset-0 flex items-center justify-center">
        <motion.div
          className="relative"
          animate={{ x: [0, -3, 5, -2, 0], y: [0, 2, -3, 1, 0] }}
          transition={{ duration: 0.3, repeat: Infinity }}
        >
          <motion.p
            className="text-xs sm:text-sm font-mono uppercase tracking-[0.3em] text-[#00ff88]"
            animate={{ opacity: [0.8, 0, 0.6, 0, 1] }}
            transition={{ duration: 0.3, repeat: Infinity }}
            style={{ textShadow: "0 0 20px #00ff88, 0 0 40px #00ff8860" }}
          >
            {GLITCH_FRAGMENTS[textIdx]}
          </motion.p>
        </motion.div>
      </div>

      {/* Chromatic aberration text */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <motion.h1
          className="text-6xl sm:text-8xl font-[var(--font-orbitron)] font-black uppercase tracking-widest"
          style={{ color: "transparent" }}
          animate={{
            opacity: [0, 0, 0.15, 0, 0.1, 0, 0.2, 0],
            textShadow: [
              "-3px 0 #ff00ff, 3px 0 #00d4ff",
              "3px 0 #ff00ff, -3px 0 #00d4ff",
              "-2px 0 #ff00ff, 2px 0 #00d4ff",
              "4px 0 #ff00ff, -4px 0 #00d4ff",
            ],
          }}
          transition={{ duration: 2, ease: "linear" }}
        >
          LIFE OS
        </motion.h1>
      </div>

      {/* Flash at the end */}
      <motion.div
        className="absolute inset-0 bg-[#00ff88] pointer-events-none"
        initial={{ opacity: 0 }}
        animate={{ opacity: [0, 0, 0, 0, 0, 0, 0, 0.8, 0] }}
        transition={{ duration: INTRO_DURATION / 1000, ease: "linear" }}
      />

      {/* Skip button */}
      <motion.button
        className="absolute bottom-6 right-6 text-[10px] font-mono uppercase tracking-[0.2em] text-[#6b7280] hover:text-[#00ff88] transition-colors z-[110]"
        onClick={onComplete}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
      >
        Skip →
      </motion.button>
    </motion.div>
  );
}

/* ─── Image Mosaic with cycling tiles ─── */
const HERO_POOL = [
  "/hero-1.jpg", "/hero-2.jpg", "/hero-3.jpg", "/hero-4.jpg", "/hero-5.jpg",
  "/hero-7.jpg", "/hero-8.jpg", "/hero-9.jpg", "/hero-10.jpg", "/hero-11.jpg", "/hero-12.jpg",
];

const TILE_STYLES = [
  { filter: "hue-rotate(10deg) saturate(1.8) brightness(1.2)", glow: "#00d4ff" },
  { filter: "hue-rotate(30deg) saturate(1.5) brightness(1.3)", glow: "#ffcc00" },
  { filter: "hue-rotate(20deg) saturate(1.6) brightness(1.2)", glow: "#ff00ff" },
  { filter: "hue-rotate(5deg) saturate(1.5) brightness(1.2)", glow: "#ff8800" },
  { filter: "hue-rotate(-5deg) saturate(1.5) brightness(1.2)", glow: "#8b5cf6" },
  { filter: "hue-rotate(-15deg) saturate(1.6) brightness(1.2)", glow: "#00ff88" },
  { filter: "hue-rotate(30deg) saturate(1.6) brightness(1.2)", glow: "#8b5cf6" },
  { filter: "hue-rotate(-20deg) saturate(1.6) brightness(1.2)", glow: "#ff3366" },
  { filter: "hue-rotate(15deg) saturate(1.5) brightness(1.3)", glow: "#00aaff" },
  { filter: "hue-rotate(25deg) saturate(1.5) brightness(1.2)", glow: "#00d4ff" },
  { filter: "hue-rotate(-10deg) saturate(1.6) brightness(1.2)", glow: "#ffcc00" },
  { filter: "hue-rotate(40deg) saturate(1.4) brightness(1.3)", glow: "#00ff88" },
  { filter: "hue-rotate(20deg) saturate(1.5) brightness(1.2)", glow: "#ff00ff" },
  { filter: "hue-rotate(-10deg) saturate(1.6) brightness(1.2)", glow: "#ff3366" },
  { filter: "hue-rotate(10deg) saturate(1.5) brightness(1.2)", glow: "#00d4ff" },
  { filter: "hue-rotate(30deg) saturate(1.4) brightness(1.3)", glow: "#8b5cf6" },
  { filter: "hue-rotate(-15deg) saturate(1.5) brightness(1.2)", glow: "#ff8800" },
  { filter: "hue-rotate(20deg) saturate(1.6) brightness(1.2)", glow: "#00ff88" },
  { filter: "hue-rotate(-25deg) saturate(1.5) brightness(1.2)", glow: "#ff00ff" },
  { filter: "hue-rotate(15deg) saturate(1.5) brightness(1.2)", glow: "#00aaff" },
  { filter: "hue-rotate(35deg) saturate(1.4) brightness(1.3)", glow: "#ffcc00" },
  { filter: "hue-rotate(-20deg) saturate(1.6) brightness(1.2)", glow: "#ff3366" },
  { filter: "hue-rotate(10deg) saturate(1.5) brightness(1.2)", glow: "#00ff88" },
  { filter: "hue-rotate(25deg) saturate(1.6) brightness(1.2)", glow: "#00d4ff" },
];

// 24 surrounding tiles (index 12 = black hole)
const CENTER_IDX = 12;

function ImageMosaic() {
  const [cycle, setCycle] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setCycle((c) => c + 1), 10000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div
      className="absolute inset-0 pointer-events-none select-none z-[1]"
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr 1fr 1fr 1fr",
        gridTemplateRows: "1fr 1fr 1fr 1fr 1fr",
        gap: "2px",
      }}
    >
      {Array.from({ length: 25 }, (_, i) => {
        if (i === CENTER_IDX) {
          // Black hole — never changes
          return (
            <motion.div
              key="blackhole"
              className="relative overflow-hidden"
              initial={{ opacity: 0, scale: 1.1 }}
              animate={{ opacity: 0.45, scale: 1 }}
              transition={{ duration: 1.6, ease, delay: 0.2 }}
            >
              <motion.div
                className="relative h-full w-full"
                animate={{ scale: [1, 1.03, 1], rotate: [0, 0.3, 0] }}
                transition={{ duration: 12, repeat: Infinity, ease: "easeInOut" }}
                style={{ filter: "drop-shadow(0 0 30px #00ff8870) drop-shadow(0 0 60px #00ff8840)" }}
              >
                <Image
                  src="/hero-6.jpg"
                  alt=""
                  fill
                  sizes="20vw"
                  className="object-cover object-center"
                  style={{
                    mixBlendMode: "lighten",
                    filter: "hue-rotate(140deg) saturate(1.3) brightness(1.5)",
                  }}
                />
              </motion.div>
            </motion.div>
          );
        }

        // Tile index for surrounding cells (skip center)
        const tileIdx = i < CENTER_IDX ? i : i - 1;
        const style = TILE_STYLES[tileIdx];
        // Each tile picks from the pool, offset by its index + cycle
        const imgSrc = HERO_POOL[(tileIdx + cycle) % HERO_POOL.length];
        const entryDelay = 0.3 + tileIdx * 0.02;

        return (
          <motion.div
            key={`tile-${i}`}
            className="relative overflow-hidden"
            initial={{ opacity: 0, scale: 0.92 }}
            animate={{ opacity: 0.18, scale: 1 }}
            transition={{ duration: 1.2, ease, delay: entryDelay }}
          >
            <AnimatePresence mode="wait">
              <motion.div
                key={`${i}-${imgSrc}`}
                className="absolute inset-0"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 1.5, ease: "easeInOut" }}
                style={{ filter: `drop-shadow(0 0 12px ${style.glow}50) drop-shadow(0 0 35px ${style.glow}25)` }}
              >
                <Image
                  src={imgSrc}
                  alt=""
                  fill
                  sizes="20vw"
                  className="object-cover object-center"
                  style={{
                    mixBlendMode: "lighten",
                    filter: style.filter,
                  }}
                />
              </motion.div>
            </AnimatePresence>
          </motion.div>
        );
      })}
    </div>
  );
}

/* ─── Auth Buttons ─── */
function AuthButtons() {
  const { isSignedIn } = useAuth();

  if (isSignedIn) {
    return (
      <Link href="/dashboard">
        <CyberButton variant="glitch" size="lg" glow>
          Enter Dashboard
        </CyberButton>
      </Link>
    );
  }

  return (
    <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
      <SignInButton mode="modal">
        <CyberButton variant="default" size="lg" glow>
          Sign In
        </CyberButton>
      </SignInButton>
      <SignUpButton mode="modal">
        <CyberButton variant="secondary" size="lg" glow>
          Initialize System
        </CyberButton>
      </SignUpButton>
    </div>
  );
}

/* ─── Typewriter ─── */
function Typewriter({ text, delay = 0 }: { text: string; delay?: number }) {
  const [displayed, setDisplayed] = useState("");
  const [started, setStarted] = useState(false);

  useEffect(() => {
    const startTimer = setTimeout(() => setStarted(true), delay);
    return () => clearTimeout(startTimer);
  }, [delay]);

  useEffect(() => {
    if (!started) return;
    let i = 0;
    const timer = setInterval(() => {
      i++;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) clearInterval(timer);
    }, 35);
    return () => clearInterval(timer);
  }, [started, text]);

  return (
    <span>
      {displayed}
      {displayed.length < text.length && started && (
        <span className="text-[#00ff88] animate-blink">_</span>
      )}
    </span>
  );
}

/* ─── Main Page ─── */
export default function Home() {
  const reducedMotion = useReducedMotion();
  const [introComplete, setIntroComplete] = useState(false);

  /* Skip intro entirely when user prefers reduced motion */
  useEffect(() => {
    if (reducedMotion) setIntroComplete(true);
  }, [reducedMotion]);

  return (
    <div className="min-h-screen bg-[#0a0a0f] overflow-hidden relative">
      {/* Glitch Intro */}
      <AnimatePresence>
        {!introComplete && !reducedMotion && (
          <GlitchIntro onComplete={() => setIntroComplete(true)} />
        )}
      </AnimatePresence>

      {/* Hero */}
      {introComplete && (
        <section className="relative min-h-screen flex items-center justify-center px-6">
          {/* Background glow orbs */}
          <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-[#00ff88]/5 rounded-full blur-[150px]" />
          <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-[#ff00ff]/5 rounded-full blur-[150px]" />

          {/* ═══ Image mosaic: CSS Grid 5×5, black hole center ═══ */}
          <ImageMosaic />

          {/* Faint scan lines (persistent) */}
          <div
            className="absolute inset-0 pointer-events-none z-[5]"
            style={{
              background:
                "repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(0,255,136,0.015) 3px, rgba(0,255,136,0.015) 4px)",
            }}
          />

          {/* Content */}
          <div className="relative z-10 max-w-3xl text-center">
            {/* Badge */}
            <motion.div
              className="inline-flex items-center gap-2 px-3 py-1.5 bg-[#00ff88]/10 border border-[#00ff88]/30 mb-8"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, ease, delay: 0.1 }}
            >
              <motion.span
                className="w-1.5 h-1.5 bg-[#00ff88]"
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ duration: 1.5, repeat: Infinity }}
              />
              <span
                className="text-[10px] font-mono uppercase tracking-[0.2em] text-[#00ff88]"
                style={{ textShadow: "0 0 8px #00ff8860" }}
              >
                System v0.1.0 // Online
              </span>
            </motion.div>

            {/* Title — slams in from above */}
            <motion.h1
              className="text-5xl sm:text-7xl lg:text-8xl font-[var(--font-orbitron)] font-black uppercase tracking-widest mb-6"
              initial={{ opacity: 0, y: -60, filter: "blur(12px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              transition={{
                type: "spring",
                stiffness: 120,
                damping: 14,
                delay: 0.2,
              }}
            >
              <span
                className="bg-clip-text text-transparent bg-gradient-to-r from-[#00ff88] via-[#00d4ff] to-[#ff00ff]"
                style={{
                  textShadow: "0 0 60px #00ff8840, 0 0 120px #ff00ff20",
                }}
              >
                Life OS
              </span>
            </motion.h1>

            {/* Neon glow pulse under title */}
            <motion.div
              className="h-px w-48 mx-auto mb-8"
              style={{
                background: "linear-gradient(90deg, transparent, #00ff88, transparent)",
              }}
              initial={{ scaleX: 0, opacity: 0 }}
              animate={{ scaleX: 1, opacity: 0.6 }}
              transition={{ duration: 0.8, ease, delay: 0.5 }}
            />

            {/* Subtitle — typewriter */}
            <motion.p
              className="text-base sm:text-lg font-mono max-w-2xl mx-auto mb-4 leading-relaxed text-[#a0a0b0]"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.6 }}
            >
              <Typewriter
                text="An AI life coach that doesn't just advise you — it acts for you."
                delay={800}
              />
            </motion.p>

            <motion.p
              className="text-sm font-mono text-[#6b7280]/70 mb-10"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 2.2 }}
            >
              Built for executive function, time blindness, and task avoidance.
            </motion.p>

            {/* CTA Buttons */}
            <motion.div
              initial={{ opacity: 0, y: 20, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{
                type: "spring",
                stiffness: 200,
                damping: 20,
                delay: 2.5,
              }}
            >
              <AuthButtons />
            </motion.div>
          </div>

          {/* Footer */}
          <motion.div
            className="absolute bottom-6 left-0 right-0 flex items-center justify-center gap-2 z-10"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 3 }}
          >
            <Zap className="w-3.5 h-3.5 text-[#00ff88]" strokeWidth={1.5} />
            <span className="text-[10px] font-mono uppercase tracking-[0.15em] text-[#6b7280]">
              © 2026 // All systems operational
            </span>
          </motion.div>
        </section>
      )}
    </div>
  );
}
