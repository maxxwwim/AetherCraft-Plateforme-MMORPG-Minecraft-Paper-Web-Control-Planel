/**
 * AetherCraft — Moteur d'Animation Scroll & Effets Immersifs (Style Evolucraft / Hyping)
 */
document.addEventListener("DOMContentLoaded", () => {
  // 1. Initialisation des Particules Stellaires Canvas
  initParticlesCanvas();

  // 2. Parallaxe & Disparition du Hero ("Scroll Fou Disparition")
  initHeroParallaxDisappearance();

  // 3. Scroll Reveal avec IntersectionObserver
  initScrollReveal();

  // 4. Cartes Interactives avec Spotlight dynamique de la souris
  initSpotlightCards();
});

/* ========================================================
   1. PARTICULES FLOTTANTES STELLAIRES
   ======================================================== */
function initParticlesCanvas() {
  const canvas = document.getElementById("particles-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  let width = (canvas.width = window.innerWidth);
  let height = (canvas.height = window.innerHeight);

  window.addEventListener("resize", () => {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
  });

  const particles = [];
  const colors = [
    "rgba(16, 185, 129, 0.75)",  // Emerald Minecraft Green
    "rgba(244, 63, 94, 0.7)",    // Blood Ruby Crimson
    "rgba(251, 191, 36, 0.75)",  // Radiant Amber Gold
    "rgba(255, 255, 255, 0.85)", // White Diamond Sparkle
  ];

  for (let i = 0; i < 45; i++) {
    particles.push({
      x: Math.random() * width,
      y: Math.random() * height,
      size: Math.random() * 2.5 + 1,
      speedY: Math.random() * 0.6 + 0.2,
      speedX: (Math.random() - 0.5) * 0.4,
      color: colors[Math.floor(Math.random() * colors.length)],
      alpha: Math.random() * 0.7 + 0.3,
      oscillation: Math.random() * Math.PI * 2,
    });
  }

  function render() {
    ctx.clearRect(0, 0, width, height);

    particles.forEach((p) => {
      p.y -= p.speedY;
      p.oscillation += 0.02;
      p.x += Math.sin(p.oscillation) * 0.4 + p.speedX;

      if (p.y < -10) {
        p.y = height + 10;
        p.x = Math.random() * width;
      }
      if (p.x < 0) p.x = width;
      if (p.x > width) p.x = 0;

      ctx.save();
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.shadowBlur = p.size * 5;
      ctx.shadowColor = p.color;
      ctx.fill();
      ctx.restore();
    });

    requestAnimationFrame(render);
  }
  render();
}

/* ========================================================
   2. EFFET HERO SCROLL PARALLAX & DISPARITION
   ======================================================== */
function initHeroParallaxDisappearance() {
  const heroContent = document.getElementById("hero-content-wrapper");
  const heroBg = document.getElementById("hero-bg-layer");
  const navbar = document.querySelector("header");

  if (!heroContent) return;

  let ticking = false;

  window.addEventListener("scroll", () => {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        const scrollY = window.scrollY;

        // Disparition progressive & flou artistique du hero
        if (scrollY < 800) {
          const fadeProgress = Math.min(1, scrollY / 460);
          const opacity = Math.max(0, 1 - fadeProgress);
          const translateY = scrollY * 0.38;
          const scale = Math.max(0.88, 1 - scrollY * 0.00035);
          const blur = Math.min(10, scrollY * 0.02);

          heroContent.style.opacity = opacity.toFixed(3);
          heroContent.style.transform = `translate3d(0, ${translateY.toFixed(1)}px, 0) scale(${scale.toFixed(3)})`;
          heroContent.style.filter = `blur(${blur.toFixed(1)}px)`;

          if (heroBg) {
            const bgScale = 1 + scrollY * 0.0005;
            const bgTranslate = scrollY * 0.2;
            heroBg.style.transform = `translate3d(0, ${bgTranslate.toFixed(1)}px, 0) scale(${bgScale.toFixed(3)})`;
          }
        }

        // Effet de navbar au scroll
        if (navbar) {
          if (scrollY > 30) {
            navbar.classList.add("navbar-scrolled");
          } else {
            navbar.classList.remove("navbar-scrolled");
          }
        }

        ticking = false;
      });
      ticking = true;
    }
  });
}

/* ========================================================
   3. SCROLL REVEAL (INTERSECTION OBSERVER)
   ======================================================== */
function initScrollReveal() {
  const revealElements = document.querySelectorAll(".reveal-on-scroll");
  if (!revealElements.length) return;

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-revealed");
          observer.unobserve(entry.target);
        }
      });
    },
    {
      threshold: 0.12,
      rootMargin: "0px 0px -50px 0px",
    }
  );

  revealElements.forEach((el) => observer.observe(el));
}

/* ========================================================
   4. SPOTLIGHT CURSOR CARD EFFECT
   ======================================================== */
function initSpotlightCards() {
  const cards = document.querySelectorAll(".spotlight-card");
  cards.forEach((card) => {
    card.addEventListener("mousemove", (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      card.style.setProperty("--mouse-x", `${x}px`);
      card.style.setProperty("--mouse-y", `${y}px`);
    });
  });
}
