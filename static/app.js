(() => {
  "use strict";

  // ---- Full-width layout toggle ----
  const WIDE_KEY = "songbook:wide";
  const wideToggle = document.getElementById("wide-toggle");
  if (wideToggle) {
    const applyWide = (on) => {
      document.documentElement.classList.toggle("is-wide", on);
      wideToggle.setAttribute("aria-pressed", String(on));
    };

    applyWide(document.documentElement.classList.contains("is-wide"));
    wideToggle.addEventListener("click", () => {
      const next = !document.documentElement.classList.contains("is-wide");
      applyWide(next);
      try {
        localStorage.setItem(WIDE_KEY, next ? "1" : "0");
      } catch (error) {}
      window.dispatchEvent(new Event("songbook:relayout"));
    });
  }

  // ---- Fit-to-screen column layout ----
  const fitToggle = document.getElementById("fit-toggle");
  const sheetScroll = document.getElementById("sheet-scroll");
  const sheetSource = document.getElementById("sheet-source");
  const sheetColumns = document.getElementById("sheet-columns");
  const fitLabel = document.getElementById("fit-label");
  const fitStatus = document.getElementById("fit-status");
  const fitNote = document.getElementById("fit-note");
  const transposeHint = document.getElementById("transpose-hint");

  // ---- Capo transposition ----
  // Chords are shown as the shapes to play with the current capo. Increasing
  // the capo therefore moves the displayed chord names down by that many
  // semitones, keeping the song at the same concert pitch.
  const NOTE_INDEX = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
  const SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
  const FLAT_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
  const DEFAULT_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"];

  const shiftNote = (letter, accidental, semitones) => {
    let index = NOTE_INDEX[letter];
    let names = DEFAULT_NAMES;
    if (accidental === "#") {
      index += 1;
      names = SHARP_NAMES;
    } else if (accidental === "b") {
      index -= 1;
      names = FLAT_NAMES;
    }
    return names[((index + semitones) % 12 + 12) % 12];
  };

  const transposeChord = (chord, semitones) => {
    if (!semitones || semitones % 12 === 0) return chord;
    const match = chord.match(/^(\*?)([A-G])([#b]?)(.*)$/);
    if (!match) return chord;

    const [, prefix, letter, accidental, suffix] = match;
    const root = shiftNote(letter, accidental, semitones);
    const shiftedSuffix = suffix.replace(
      /\/([A-G])([#b]?)(?![A-Za-z0-9#b])/g,
      (_slash, bassLetter, bassAccidental) =>
        `/${shiftNote(bassLetter, bassAccidental, semitones)}`
    );
    return `${prefix}${root}${shiftedSuffix}`;
  };

  const applyCapoTranspose = (value) => {
    if (!sheetSource) return;
    const capo = Math.min(12, Math.max(0, Number.parseInt(value, 10) || 0));
    const semitones = -capo;

    sheetSource.querySelectorAll(".chord[data-chord]").forEach((span) => {
      span.textContent = transposeChord(span.dataset.chord, semitones);
    });
    if (transposeHint) {
      transposeHint.textContent = capo ? `Chords for capo ${capo}` : "Original chords";
    }
    window.dispatchEvent(new Event("songbook:sheet-updated"));
  };

  if (fitToggle && sheetScroll && sheetSource && sheetColumns) {
    const FIT_KEY = "songbook:fit";
    const FIT_MIN = 8;
    const FIT_MAX = 18;
    const root = document.documentElement;
    let sourceHTML = sheetSource.innerHTML;
    let lines = sourceHTML.split("\n");
    const gap = 2 * (parseFloat(getComputedStyle(root).fontSize) || 16);
    let fitOn = false;
    let layoutTimer = 0;
    let attempts = 0;

    let plainLines = lines.map((line) => {
      const element = document.createElement("textarea");
      element.innerHTML = line.replace(/<[^>]*>/g, "");
      return element.value;
    });

    // Section headers are kept as whole blocks. Bracketed headers such as
    // [Verse] are the most common, but many chord sheets use labels
    // like "Verse 1:" or "C1:". The renderer's bracket pattern stays the same;
    // this looser detection is only for choosing column breaks.
    const SECTION_RE = /^\s*\[[^\[\]\n]{1,80}\](?:\s*\([^)\n]*\))?\s*$/;
    const SECTION_ONLY_RE =
      /^\s*(?:(?:intro|outro|verse|pre[- ]?chorus|post[- ]?chorus|chorus|bridge|middle[- ]?eight|guitar[- ]?solo|solo|interlude|instrumental|breakdown|riff|hook|refrain|coda|tag|vamp|turnaround)\s*\d*|(?:v|pc)\s*\d+)\s*(?:\([^)\n]*\))?\s*$/i;
    const SECTION_LABEL_RE =
      /^\s*(?:(?:intro|outro|verse|pre[- ]?chorus|post[- ]?chorus|chorus|bridge|middle[- ]?eight|guitar[- ]?solo|solo|interlude|instrumental|breakdown|riff|hook|refrain|coda|tag|vamp|turnaround)(?:\s*\d+)?|(?:v|pc|c)\s*\d+)\s*(?:\([^)\n]*\))?\s*(?::|\.|\)|-)\s*/i;
    const CHORD_TOKEN_RE =
      /^\(?(?:\*?[A-G](?:#|b)?(?:(?:maj|min|m|dim|aug|sus|add|no|°|ø|Δ)\d*|[#b]?\d+)*(?:\([#b]?\d+\))*(?:\/(?:[A-G](?:#|b)?|\d+))?|N\.?C\.?|x|X|-|\|)\)?$/;

    const isChordLine = (line) => {
      const tokens = line
        .trim()
        .replace(/[|:]/g, " ")
        .split(/\s+/)
        .filter(Boolean);
      return tokens.length > 0 && tokens.every((token) => CHORD_TOKEN_RE.test(token));
    };

    const starts = new Set();
    plainLines.forEach((line, index) => {
      if (SECTION_RE.test(line) || SECTION_ONLY_RE.test(line)) {
        starts.add(index);
      } else if (SECTION_LABEL_RE.test(line)) {
        // "V1: first line" is normally preceded by that section's chord line.
        // Break before the chord line, not between the chords and the lyric.
        starts.add(
          index > 0 && isChordLine(plainLines[index - 1]) ? index - 1 : index
        );
      }
    });
    const sectionStarts = [...starts].sort((a, b) => a - b);

    // Hidden copy of the whole song, used to measure the widest line at any size.
    const measurer = document.createElement("pre");
    measurer.className = "sheet";
    measurer.setAttribute("aria-hidden", "true");
    measurer.innerHTML = sourceHTML;
    Object.assign(measurer.style, {
      position: "absolute",
      left: "-9999px",
      top: "0",
      width: "max-content",
      visibility: "hidden",
      pointerEvents: "none",
      whiteSpace: "pre",
      lineHeight: "1.45",
    });
    document.body.appendChild(measurer);
    fitToggle.hidden = false;

    const measure = (size) => {
      measurer.style.fontSize = `${size}px`;
      return {
        width: Math.ceil(measurer.getBoundingClientRect().width) + 1,
        lineHeight: parseFloat(getComputedStyle(measurer).lineHeight) || size * 1.45,
      };
    };

    const availableArea = () => {
      const style = getComputedStyle(sheetScroll);
      return {
        width:
          sheetScroll.clientWidth -
          parseFloat(style.paddingLeft) -
          parseFloat(style.paddingRight),
        height:
          sheetScroll.clientHeight -
          parseFloat(style.paddingTop) -
          parseFloat(style.paddingBottom),
      };
    };

    const buildSectionRanges = (maxColumns, maxLines) => {
      if (!sectionStarts.length) return null;

      const ranges = [];
      let start = 0;

      while (start < lines.length) {
        if (ranges.length >= maxColumns) return null;

        const limit = Math.min(lines.length, start + maxLines);
        if (limit >= lines.length) {
          ranges.push([start, lines.length]);
          break;
        }

        // Pack as many complete sections into this column as possible.
        let boundary = null;
        for (const candidate of sectionStarts) {
          if (candidate <= start) continue;
          if (candidate > limit) break;
          boundary = candidate;
        }
        if (boundary !== null) {
          ranges.push([start, boundary]);
          start = boundary;
          continue;
        }

        // No section boundary fits. That is allowed only in the preamble;
        // breaking inside a section would cut it in half, so reject this size.
        let insideSection = false;
        for (const candidate of sectionStarts) {
          if (candidate <= start) {
            insideSection = true;
          } else {
            break;
          }
        }
        if (insideSection) return null;

        // The preamble is filler/notes. Split it at a nearby blank line, or
        // at the hard column limit when there is no natural break.
        let end = limit;
        let blankEnd = null;
        for (let distance = 0; distance <= 4 && blankEnd === null; distance += 1) {
          for (const index of [limit - distance, limit + distance]) {
            if (index <= start || index >= limit) continue;
            if (plainLines[index].trim() === "") {
              blankEnd = index + 1;
              break;
            }
          }
        }
        if (blankEnd !== null) end = blankEnd;
        ranges.push([start, end]);
        start = end;
      }

      return ranges;
    };

    // Last-resort layout for tabs too tall to fit even at 8px. We still keep
    // columns on section boundaries and let the reading view scroll vertically
    // rather than slicing a verse/chorus between columns.
    const buildOverflowSectionRanges = (maxColumns) => {
      if (!sectionStarts.length || maxColumns < 1) return null;

      const boundaries = sectionStarts.filter(
        (index) => index > 0 && index < lines.length
      );
      const maxBreaks = Math.min(maxColumns - 1, boundaries.length);
      if (maxBreaks < 1) return [[0, lines.length]];

      const breaks = [];
      let start = 0;
      for (let index = 0; index < maxBreaks; index += 1) {
        const remainingColumns = maxBreaks - index + 1;
        const target = start + (lines.length - start) / remainingColumns;
        const remainingBreaks = maxBreaks - index - 1;
        const maxBoundaryIndex = boundaries.length - remainingBreaks - 1;
        let best = null;

        for (let candidateIndex = 0; candidateIndex <= maxBoundaryIndex; candidateIndex += 1) {
          const boundary = boundaries[candidateIndex];
          if (boundary <= start) continue;
          if (
            best === null ||
            Math.abs(boundary - target) < Math.abs(best - target)
          ) {
            best = boundary;
          }
        }

        if (best === null) break;
        breaks.push(best);
        start = best;
      }

      const ranges = [];
      let rangeStart = 0;
      breaks.forEach((boundary) => {
        ranges.push([rangeStart, boundary]);
        rangeStart = boundary;
      });
      ranges.push([rangeStart, lines.length]);
      return ranges;
    };

    const chooseLayout = (available) => {
      for (let size = FIT_MAX; size >= FIT_MIN; size -= 0.5) {
        const metrics = measure(size);
        const columnsByWidth = Math.floor(
          (available.width + gap) / (metrics.width + gap)
        );
        const linesPerColumn = Math.floor(available.height / metrics.lineHeight);
        if (columnsByWidth < 1 || linesPerColumn < 1) continue;

        if (sectionStarts.length) {
          const ranges = buildSectionRanges(columnsByWidth, linesPerColumn);
          if (ranges) {
            return {
              ...metrics,
              size,
              columnsByWidth,
              linesPerColumn,
              ranges,
              overflow: false,
            };
          }
          continue;
        }

        if (columnsByWidth * linesPerColumn >= lines.length) {
          return {
            ...metrics,
            size,
            columnsByWidth,
            linesPerColumn,
            overflow: false,
          };
        }
      }

      const metrics = measure(FIT_MIN);
      return {
        ...metrics,
        size: FIT_MIN,
        columnsByWidth: Math.max(
          1,
          Math.floor((available.width + gap) / (metrics.width + gap))
        ),
        linesPerColumn: Math.max(
          1,
          Math.floor(available.height / metrics.lineHeight)
        ),
        overflow: true,
      };
    };

    // Split lines into columns. A new column starts on a section header when
    // one fits, so a verse, chorus or bridge is never cut in half. Blank lines
    // and the balanced target are fallbacks for tabs without section markers
    // (or for a section that is taller than an entire column).
    const buildRanges = (columnCount, maxLines, adjust) => {
      const ranges = [];
      let start = 0;

      for (let column = 0; column < columnCount && start < lines.length; column++) {
        const remainingColumns = columnCount - column;
        const remainingLines = lines.length - start;
        const minEnd = maxLines
          ? Math.max(
              start + 1,
              lines.length - (remainingColumns - 1) * maxLines
            )
          : start + 1;
        let end = start + Math.ceil(remainingLines / remainingColumns);

        if (maxLines) end = Math.min(end, start + maxLines);
        end = Math.min(lines.length, Math.max(end, minEnd));

        if (adjust && end < lines.length) {
          const lower = Math.max(start + 1, minEnd);
          const upper = maxLines
            ? Math.min(lines.length, start + maxLines)
            : lines.length;
          let sectionEnd = null;

          sectionStarts.forEach((boundary) => {
            if (boundary < lower || boundary > upper) return;
            if (
              sectionEnd === null ||
              Math.abs(boundary - end) < Math.abs(sectionEnd - end)
            ) {
              sectionEnd = boundary;
            }
          });

          if (sectionEnd !== null) {
            end = sectionEnd;
          } else {
            const target = end;
            let blankEnd = null;
            for (
              let distance = 0;
              distance <= 4 && blankEnd === null;
              distance += 1
            ) {
              for (const index of [target - distance, target + distance]) {
                if (index < lower || index >= upper) continue;
                if (plainLines[index].trim() === "") {
                  blankEnd = index + 1;
                  break;
                }
              }
            }
            if (blankEnd !== null) end = blankEnd;
          }
        }

        ranges.push([start, end]);
        start = end;
      }

      if (start < lines.length) {
        if (ranges.length) {
          ranges[ranges.length - 1][1] = lines.length;
        } else {
          ranges.push([0, lines.length]);
        }
      }
      return ranges;
    };

    const renderColumns = () => {
      if (!fitOn) return;

      const available = availableArea();
      if (available.width < 60 || available.height < 60) {
        if (attempts < 10) {
          attempts += 1;
          window.setTimeout(renderColumns, 60);
        }
        return;
      }

      const chosen = chooseLayout(available);
      let ranges;
      if (chosen.overflow) {
        ranges =
          buildOverflowSectionRanges(chosen.columnsByWidth) ||
          buildRanges(chosen.columnsByWidth, null, false);
      } else if (chosen.ranges) {
        ranges = chosen.ranges;
      } else {
        const columnCount = Math.max(
          1,
          Math.min(
            chosen.columnsByWidth,
            Math.ceil(lines.length / chosen.linesPerColumn)
          )
        );
        ranges = buildRanges(columnCount, chosen.linesPerColumn, true);
      }

      const fragment = document.createDocumentFragment();
      ranges.forEach(([start, end]) => {
        const column = document.createElement("pre");
        column.className = "sheet sheet-column";
        column.style.width = `${chosen.width}px`;
        column.style.fontSize = `${chosen.size}px`;
        column.style.lineHeight = "1.45";
        column.innerHTML = lines.slice(start, end).join("\n");
        fragment.appendChild(column);
      });

      sheetColumns.replaceChildren(fragment);
      sheetColumns.style.setProperty("--fit-font-size", `${chosen.size}px`);
      sheetColumns.hidden = false;

      const tallest = Array.from(sheetColumns.children).reduce(
        (height, column) => Math.max(height, column.getBoundingClientRect().height),
        0
      );
      const overflowing =
        chosen.overflow ||
        chosen.width > available.width + 1 ||
        tallest > available.height + 1;

      sheetScroll.classList.toggle("is-overflowing", overflowing);
      if (fitNote) fitNote.hidden = !overflowing;
      if (fitStatus) {
        fitStatus.textContent = `Fit view: ${ranges.length} column${
          ranges.length === 1 ? "" : "s"
        }, ${chosen.size} pixel text${overflowing ? ", scroll for the rest" : ""}.`;
      }
    };

    window.addEventListener("songbook:sheet-updated", () => {
      sourceHTML = sheetSource.innerHTML;
      lines = sourceHTML.split("\n");
      plainLines = lines.map((line) => {
        const element = document.createElement("textarea");
        element.innerHTML = line.replace(/<[^>]*>/g, "");
        return element.value;
      });
      measurer.innerHTML = sourceHTML;
      if (fitOn) {
        attempts = 0;
        renderColumns();
      }
    });

    const enterFit = () => {
      if (fitOn) return;
      fitOn = true;
      attempts = 0;
      root.classList.add("fit-mode");
      fitToggle.setAttribute("aria-pressed", "true");
      if (fitLabel) fitLabel.textContent = "Exit fit";
      try {
        localStorage.setItem(FIT_KEY, "1");
      } catch (error) {}

      window.scrollTo(0, 0);
      sheetSource.hidden = true;
      sheetColumns.hidden = false;
      sheetScroll.scrollTop = 0;
      requestAnimationFrame(() => requestAnimationFrame(renderColumns));
    };

    const exitFit = () => {
      if (!fitOn) return;
      fitOn = false;
      root.classList.remove("fit-mode");
      fitToggle.setAttribute("aria-pressed", "false");
      if (fitLabel) fitLabel.textContent = "Fit to screen";
      try {
        localStorage.setItem(FIT_KEY, "0");
      } catch (error) {}

      sheetColumns.hidden = true;
      sheetSource.hidden = false;
      sheetColumns.replaceChildren();
      sheetScroll.classList.remove("is-overflowing");
      if (fitNote) fitNote.hidden = true;
      if (fitStatus) fitStatus.textContent = "";
    };

    fitToggle.addEventListener("click", () => {
      if (fitOn) {
        exitFit();
      } else {
        enterFit();
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && fitOn) {
        exitFit();
        fitToggle.focus();
      }
    });

    const scheduleLayout = () => {
      if (!fitOn) return;
      window.clearTimeout(layoutTimer);
      layoutTimer = window.setTimeout(() => {
        attempts = 0;
        renderColumns();
      }, 120);
    };

    window.addEventListener("resize", scheduleLayout);
    window.addEventListener("songbook:relayout", scheduleLayout);

    let startInFit = false;
    try {
      startInFit = localStorage.getItem(FIT_KEY) === "1";
    } catch (error) {}
    if (startInFit && window.innerWidth >= 760) enterFit();
  }

  // ---- Add form: show progress while the server saves the song ----
  const addForm = document.querySelector("[data-add-form]");
  if (addForm) {
    addForm.addEventListener("submit", () => {
      const button = addForm.querySelector('button[type="submit"]');
      if (!button || button.disabled) return;
      button.disabled = true;
      button.textContent = "Adding…";
    });
  }

  // ---- Delete confirmation ----
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) {
        event.preventDefault();
      }
    });
  });

  // ---- Capo + performance autosave ----
  const form = document.getElementById("settings-form");
  if (!form) return;

  const capoInput = form.querySelector("#capo");
  const stars = form.querySelector("#stars");
  const starButtons = Array.from(form.querySelectorAll(".star"));
  const clearButton = form.querySelector("#clear-rating");
  const status = form.querySelector("#save-status");
  const saveButton = form.querySelector("#save-btn");

  let rating = Number(stars?.dataset.rating || 0);
  let timer = null;
  let statusTimer = null;

  const clampCapo = (value) => {
    const number = Number.parseInt(value, 10);
    if (Number.isNaN(number)) return 0;
    return Math.min(12, Math.max(0, number));
  };

  const setStatus = (text, tone = "") => {
    if (!status) return;
    status.textContent = text;
    if (tone) {
      status.dataset.tone = tone;
    } else {
      delete status.dataset.tone;
    }
  };

  const paint = () => {
    starButtons.forEach((button) => {
      const value = Number(button.dataset.value);
      button.classList.toggle("is-on", value <= rating);
      button.setAttribute("aria-pressed", String(value <= rating));
    });
    if (clearButton) clearButton.hidden = rating === 0;
  };

  const preview = (value) => {
    starButtons.forEach((button) => {
      const starValue = Number(button.dataset.value);
      button.classList.toggle("is-on", starValue <= value);
    });
  };

  const save = async () => {
    window.clearTimeout(timer);
    window.clearTimeout(statusTimer);

    const body = new FormData(form);
    if (capoInput) {
      capoInput.value = String(clampCapo(capoInput.value));
      body.set("capo", capoInput.value);
    }
    body.set("rating", String(rating));

    setStatus("Saving…");
    try {
      const response = await fetch(form.action, {
        method: "POST",
        body,
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setStatus("Saved", "ok");
      statusTimer = window.setTimeout(() => setStatus(""), 1800);
    } catch (error) {
      setStatus("Couldn't save", "error");
    }
  };

  if (capoInput) {
    capoInput.addEventListener("input", () => {
      if (capoInput.value.trim() === "") return;
      applyCapoTranspose(capoInput.value);
      window.clearTimeout(timer);
      timer = window.setTimeout(save, 600);
    });

    capoInput.addEventListener("change", () => {
      capoInput.value = String(clampCapo(capoInput.value));
      applyCapoTranspose(capoInput.value);
      save();
    });

    capoInput.addEventListener("blur", () => {
      if (capoInput.value.trim() === "") {
        capoInput.value = "0";
        applyCapoTranspose(capoInput.value);
        save();
      }
    });

    form.querySelectorAll("[data-step]").forEach((button) => {
      button.addEventListener("click", () => {
        const step = Number(button.dataset.step);
        capoInput.value = String(clampCapo(Number(capoInput.value || 0) + step));
        applyCapoTranspose(capoInput.value);
        save();
      });
    });
  }

  starButtons.forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      rating = Number(button.dataset.value);
      paint();
      save();
    });

    button.addEventListener("pointerenter", () => preview(Number(button.dataset.value)));
  });

  if (stars) {
    stars.addEventListener("pointerleave", paint);
  }

  if (clearButton) {
    clearButton.addEventListener("click", (event) => {
      event.preventDefault();
      rating = 0;
      paint();
      save();
    });
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (capoInput) {
      capoInput.value = String(clampCapo(capoInput.value));
      applyCapoTranspose(capoInput.value);
    }
    save();
  });

  paint();
})();
