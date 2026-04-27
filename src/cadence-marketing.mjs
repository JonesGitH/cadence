import path from "node:path";
import { writeFile } from "node:fs/promises";
import { readFileSync } from "node:fs";
import {
  Presentation,
  PresentationFile,
  row,
  column,
  grid,
  layers,
  panel,
  text,
  image,
  shape,
  rule,
  fill,
  hug,
  fixed,
  wrap,
  grow,
  fr,
  auto,
} from "@oai/artifact-tool";

const ROOT = path.resolve(".");
const OUT = path.join(ROOT, "output", "output.pptx");
const SCRATCH = path.join(ROOT, "scratch");
const img = (name) => path.join(ROOT, "sample_output", "screenshots", name);

const W = 1920;
const H = 1080;

const color = {
  ink: "#121826",
  navy: "#0F172A",
  slate: "#48566A",
  muted: "#66748A",
  blue: "#2563EB",
  blue2: "#60A5FA",
  purple: "#7C3AED",
  violet: "#A78BFA",
  orange: "#F97316",
  amber: "#FDBA74",
  paper: "#F8FAFC",
  mist: "#EEF4FF",
  white: "#FFFFFF",
  line: "#D8E1EE",
  green: "#10B981",
};

const fonts = {
  display: "Aptos Display",
  body: "Aptos",
};

const presentation = Presentation.create({
  slideSize: { width: W, height: H },
});

function addSlide(root, background = color.paper) {
  const slide = presentation.slides.add();
  slide.compose(
    layers({ name: "stage", width: fill, height: fill }, [
      shape({ name: "background", width: fill, height: fill, fill: background }),
      root,
    ]),
    { frame: { left: 0, top: 0, width: W, height: H }, baseUnit: 8 },
  );
  return slide;
}

function headline(value, opts = {}) {
  return text(value, {
    name: opts.name ?? "slide-title",
    width: opts.width ?? wrap(1240),
    height: hug,
    style: {
      fontFace: fonts.display,
      fontSize: opts.size ?? 66,
      bold: true,
      color: opts.color ?? color.ink,
    },
  });
}

function subline(value, opts = {}) {
  return text(value, {
    name: opts.name ?? "slide-subtitle",
    width: opts.width ?? wrap(1040),
    height: hug,
    style: {
      fontFace: fonts.body,
      fontSize: opts.size ?? 28,
      color: opts.color ?? color.slate,
    },
  });
}

function eyebrow(value, opts = {}) {
  return text(value.toUpperCase(), {
    name: opts.name ?? "eyebrow",
    width: opts.width ?? wrap(720),
    height: hug,
    style: {
      fontFace: fonts.body,
      fontSize: opts.size ?? 18,
      bold: true,
      color: opts.color ?? color.orange,
    },
  });
}

function screenshot(pathname, alt) {
  const dataUrl = `data:image/png;base64,${readFileSync(pathname).toString("base64")}`;
  return image({
    name: alt.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
    dataUrl,
    contentType: "image/png",
    width: fill,
    height: fill,
    fit: "contain",
    borderRadius: 18,
    alt,
  });
}

function pill(value, fillColor = color.mist, textColor = color.blue) {
  return panel(
    {
      name: `pill-${value.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`,
      width: hug,
      height: hug,
      padding: { x: 20, y: 10 },
      fill: fillColor,
      borderRadius: "rounded-full",
    },
    text(value, {
      width: hug,
      height: hug,
      style: { fontFace: fonts.body, fontSize: 18, bold: true, color: textColor },
    }),
  );
}

function proofItem(number, title, body) {
  return row({ name: `proof-${number}`, width: fill, height: hug, gap: 20, align: "start" }, [
    text(number, {
      width: fixed(68),
      height: hug,
      style: { fontFace: fonts.display, fontSize: 48, bold: true, color: color.blue },
    }),
    column({ width: fill, height: hug, gap: 8 }, [
      text(title, {
        width: fill,
        height: hug,
        style: { fontFace: fonts.display, fontSize: 30, bold: true, color: color.ink },
      }),
      text(body, {
        width: fill,
        height: hug,
        style: { fontFace: fonts.body, fontSize: 22, color: color.slate },
      }),
    ]),
  ]);
}

function featureRow(label, detail, accent = color.blue) {
  return row({ width: fill, height: hug, gap: 18, align: "center" }, [
    shape({ width: fixed(14), height: fixed(14), fill: accent, borderRadius: "rounded-full" }),
    text(label, {
      width: fixed(300),
      height: hug,
      style: { fontFace: fonts.display, fontSize: 25, bold: true, color: color.ink },
    }),
    text(detail, {
      width: fill,
      height: hug,
      style: { fontFace: fonts.body, fontSize: 22, color: color.slate },
    }),
  ]);
}

// 1. Cover
addSlide(
  grid(
    {
      name: "cover-root",
      width: fill,
      height: fill,
      columns: [fr(0.95), fr(1.05)],
      rows: [fr(1)],
      padding: { x: 92, y: 74 },
      columnGap: 52,
      alignItems: "center",
    },
    [
      column({ width: fill, height: hug, gap: 24 }, [
        eyebrow("Cadence marketing deck", { color: color.amber }),
        text("Your consulting rhythm.", {
          name: "cover-title",
          width: fill,
          height: hug,
          style: {
            fontFace: fonts.display,
            fontSize: 92,
            bold: true,
            color: color.white,
          },
        }),
        text("A local Windows app that turns Microsoft 365 calendar sessions into polished invoices for educational therapists, tutors, and solo practitioners.", {
          name: "cover-subtitle",
          width: wrap(720),
          height: hug,
          style: { fontFace: fonts.body, fontSize: 28, color: "#C9D6EA" },
        }),
        row({ width: hug, height: hug, gap: 14, padding: { y: 8 } }, [
          pill("Calendar", "#1E3A8A", "#BFDBFE"),
          pill("Invoices", "#4C1D95", "#DDD6FE"),
          pill("Local data", "#7C2D12", "#FED7AA"),
        ]),
      ]),
      panel(
        {
          name: "cover-product-screenshot",
          width: fill,
          height: fixed(720),
          padding: 18,
          fill: "#172033",
          borderRadius: 28,
        },
        screenshot(img("05_after_dashboard.png"), "Cadence dashboard screenshot"),
      ),
    ],
  ),
  color.navy,
);

// 2. Problem
addSlide(
  grid(
    {
      name: "problem-root",
      width: fill,
      height: fill,
      columns: [fr(1.05), fr(0.95)],
      rows: [auto, fr(1)],
      padding: { x: 92, y: 76 },
      columnGap: 68,
      rowGap: 46,
    },
    [
      column({ columnSpan: 2, width: fill, height: hug, gap: 18 }, [
        eyebrow("The admin drag"),
        headline("Solo practices should not need a billing department."),
        subline("Cadence is positioned around a simple promise: keep the practitioner in session mode while invoices, payments, and reporting stay organized."),
      ]),
      column({ width: fill, height: fill, gap: 26, justify: "center" }, [
        proofItem("01", "Calendar sessions already know the work", "No duplicate entry when appointments can become invoice line items."),
        proofItem("02", "Parents need clean, credible PDFs", "Professional invoices are created with session detail, billing address, and payment instructions."),
        proofItem("03", "Tax season needs a paper trail", "Payment status, annual summaries, and CSV export keep income visible."),
      ]),
      panel(
        {
          width: fill,
          height: fill,
          padding: 28,
          fill: color.white,
          borderRadius: 22,
        },
        screenshot(img("09_after_invoice_history.png"), "Invoice history screenshot"),
      ),
    ],
  ),
);

// 3. Workflow
addSlide(
  column(
    {
      name: "workflow-root",
      width: fill,
      height: fill,
      padding: { x: 94, y: 78 },
      gap: 46,
    },
    [
      column({ width: fill, height: hug, gap: 18 }, [
        eyebrow("The core story"),
        headline("From session calendar to sent invoice in one clean flow.", { width: wrap(1300) }),
      ]),
      grid(
        {
          width: fill,
          height: fill,
          columns: [fr(1), auto, fr(1), auto, fr(1), auto, fr(1)],
          rows: [fr(1)],
          columnGap: 22,
          alignItems: "center",
        },
        [
          panel({ width: fill, height: fixed(330), padding: 32, fill: color.white, borderRadius: 18 }, column({ width: fill, height: fill, gap: 18, justify: "center" }, [
            text("Microsoft 365 calendar", { width: fill, height: hug, style: { fontFace: fonts.display, fontSize: 34, bold: true, color: color.ink } }),
            text("Cadence reads selected Outlook calendars through Microsoft Graph. Outlook does not need to be open.", { width: fill, height: hug, style: { fontFace: fonts.body, fontSize: 23, color: color.slate } }),
          ])),
          text(">", { width: fixed(42), height: hug, style: { fontFace: fonts.display, fontSize: 42, bold: true, color: color.orange } }),
          panel({ width: fill, height: fixed(330), padding: 32, fill: color.white, borderRadius: 18 }, column({ width: fill, height: fill, gap: 18, justify: "center" }, [
            text("Student matching", { width: fill, height: hug, style: { fontFace: fonts.display, fontSize: 34, bold: true, color: color.ink } }),
            text("Appointment titles are matched against student initials so billable sessions can be found quickly.", { width: fill, height: hug, style: { fontFace: fonts.body, fontSize: 23, color: color.slate } }),
          ])),
          text(">", { width: fixed(42), height: hug, style: { fontFace: fonts.display, fontSize: 42, bold: true, color: color.orange } }),
          panel({ width: fill, height: fixed(330), padding: 32, fill: color.white, borderRadius: 18 }, column({ width: fill, height: fill, gap: 18, justify: "center" }, [
            text("PDF invoice", { width: fill, height: hug, style: { fontFace: fonts.display, fontSize: 34, bold: true, color: color.ink } }),
            text("Every selected session becomes a line item at the configured rate, with the right bill-to details.", { width: fill, height: hug, style: { fontFace: fonts.body, fontSize: 23, color: color.slate } }),
          ])),
          text(">", { width: fixed(42), height: hug, style: { fontFace: fonts.display, fontSize: 42, bold: true, color: color.orange } }),
          panel({ width: fill, height: fixed(330), padding: 32, fill: color.white, borderRadius: 18 }, column({ width: fill, height: fill, gap: 18, justify: "center" }, [
            text("Email + tracking", { width: fill, height: hug, style: { fontFace: fonts.display, fontSize: 34, bold: true, color: color.ink } }),
            text("Send through Microsoft 365, save to Sent Items, then track payment status and income.", { width: fill, height: hug, style: { fontFace: fonts.body, fontSize: 23, color: color.slate } }),
          ])),
        ],
      ),
    ],
  ),
);

// 4. Product proof: invoice creation
addSlide(
  grid(
    {
      name: "invoice-root",
      width: fill,
      height: fill,
      columns: [fr(0.78), fr(1.22)],
      padding: { x: 92, y: 76 },
      columnGap: 56,
      alignItems: "center",
    },
    [
      column({ width: fill, height: hug, gap: 24 }, [
        eyebrow("Product proof"),
        headline("The main action is exactly where a practitioner expects it.", { width: fill }),
        subline("Choose a client and month, pull sessions from Outlook, and generate the invoice without rebuilding the month by hand.", { width: fill }),
        rule({ width: fixed(240), stroke: color.orange, weight: 5 }),
        featureRow("Configured rate", "Uses the practitioner’s standard or student-specific session rate.", color.orange),
        featureRow("Month folders", "Saves invoices into month-based PDF folders automatically.", color.blue),
        featureRow("Duplicate guard", "Prevents accidental duplicate invoices unless overridden.", color.green),
      ]),
      panel(
        {
          width: fill,
          height: fixed(720),
          padding: 18,
          fill: color.white,
          borderRadius: 24,
        },
        screenshot(img("08_after_new_invoice.png"), "New invoice screenshot"),
      ),
    ],
  ),
);

// 5. Practice data
addSlide(
  grid(
    {
      name: "practice-root",
      width: fill,
      height: fill,
      columns: [fr(1.1), fr(0.9)],
      rows: [auto, fr(1)],
      padding: { x: 92, y: 76 },
      columnGap: 52,
      rowGap: 36,
    },
    [
      column({ columnSpan: 2, width: fill, height: hug, gap: 18 }, [
        eyebrow("Practice management"),
        headline("Cadence keeps the business context close to the billing moment.", { width: wrap(1340) }),
      ]),
      panel(
        {
          width: fill,
          height: fill,
          padding: 18,
          fill: color.white,
          borderRadius: 24,
        },
        screenshot(img("07_after_clients.png"), "Clients screenshot"),
      ),
      column({ width: fill, height: fill, gap: 24, justify: "center" }, [
        featureRow("Client records", "Student, parent, services, grade, birthday, and billing fields in one place.", color.blue),
        featureRow("Flexible bill-to", "Parent 1, Parent 2, or custom payer details flow into the PDF.", color.purple),
        featureRow("Import-ready", "Bulk student import from Excel helps a practice get live faster.", color.orange),
        featureRow("Archive-friendly", "Keep current families clean while preserving history.", color.green),
      ]),
    ],
  ),
);

// 6. Trust
addSlide(
  grid(
    {
      name: "trust-root",
      width: fill,
      height: fill,
      columns: [fr(0.86), fr(1.14)],
      padding: { x: 92, y: 76 },
      columnGap: 64,
      alignItems: "center",
    },
    [
      column({ width: fill, height: hug, gap: 24 }, [
        eyebrow("Trust position"),
        headline("No subscription. No hosted database. No extra billing portal.", { width: fill }),
        subline("Cadence runs on the practitioner’s own Windows PC, connects to their Microsoft 365 account, and stores practice data locally.", { width: fill }),
      ]),
      grid(
        {
          width: fill,
          height: hug,
          columns: [fr(1), fr(1)],
          rows: [auto, auto],
          columnGap: 24,
          rowGap: 24,
        },
        [
          panel({ width: fill, height: fixed(220), padding: 28, fill: color.white, borderRadius: 18 }, column({ width: fill, height: fill, gap: 12, justify: "center" }, [
            text("Local-first", { width: fill, height: hug, style: { fontFace: fonts.display, fontSize: 32, bold: true, color: color.ink } }),
            text("Everything runs on the user’s PC; no Cadence cloud service is required.", { width: fill, height: hug, style: { fontFace: fonts.body, fontSize: 22, color: color.slate } }),
          ])),
          panel({ width: fill, height: fixed(220), padding: 28, fill: color.white, borderRadius: 18 }, column({ width: fill, height: fill, gap: 12, justify: "center" }, [
            text("Microsoft 365 native", { width: fill, height: hug, style: { fontFace: fonts.display, fontSize: 32, bold: true, color: color.ink } }),
            text("Uses Microsoft Graph for calendar reads and invoice email sending.", { width: fill, height: hug, style: { fontFace: fonts.body, fontSize: 22, color: color.slate } }),
          ])),
          panel({ width: fill, height: fixed(220), padding: 28, fill: color.white, borderRadius: 18 }, column({ width: fill, height: fill, gap: 12, justify: "center" }, [
            text("Installable", { width: fill, height: hug, style: { fontFace: fonts.display, fontSize: 32, bold: true, color: color.ink } }),
            text("A Windows installer can include everything needed; no Python setup for end users.", { width: fill, height: hug, style: { fontFace: fonts.body, fontSize: 22, color: color.slate } }),
          ])),
          panel({ width: fill, height: fixed(220), padding: 28, fill: color.white, borderRadius: 18 }, column({ width: fill, height: fill, gap: 12, justify: "center" }, [
            text("Backup + OneDrive", { width: fill, height: hug, style: { fontFace: fonts.display, fontSize: 32, bold: true, color: color.ink } }),
            text("Built-in backup and configurable storage folders support practical two-PC workflows.", { width: fill, height: hug, style: { fontFace: fonts.body, fontSize: 22, color: color.slate } }),
          ])),
        ],
      ),
    ],
  ),
);

// 7. Settings proof
addSlide(
  grid(
    {
      name: "settings-root",
      width: fill,
      height: fill,
      columns: [fr(1.12), fr(0.88)],
      padding: { x: 92, y: 76 },
      columnGap: 54,
      alignItems: "center",
    },
    [
      panel(
        {
          width: fill,
          height: fixed(720),
          padding: 18,
          fill: color.white,
          borderRadius: 24,
        },
        screenshot(img("06_after_settings.png"), "Settings screenshot"),
      ),
      column({ width: fill, height: hug, gap: 26 }, [
        eyebrow("Setup story"),
        headline("Configuration is front-loaded so monthly billing stays simple.", { width: fill, size: 60 }),
        subline("Business identity, rate, Microsoft 365 connection, calendar selection, storage, backup, and import live in the settings flow.", { width: fill }),
        rule({ width: fixed(220), stroke: color.purple, weight: 5 }),
        text("Marketing angle: Cadence feels purpose-built because every setting maps to a real solo-practice chore.", {
          width: fill,
          height: hug,
          style: { fontFace: fonts.body, fontSize: 25, color: color.ink, bold: true },
        }),
      ]),
    ],
  ),
);

// 8. Close
addSlide(
  grid(
    {
      name: "close-root",
      width: fill,
      height: fill,
      columns: [fr(1.1), fr(0.9)],
      padding: { x: 94, y: 78 },
      columnGap: 58,
      alignItems: "center",
    },
    [
      column({ width: fill, height: hug, gap: 26 }, [
        eyebrow("Launch message", { color: color.amber }),
        text("Make monthly billing feel like closing the loop.", {
          name: "close-title",
          width: fill,
          height: hug,
          style: { fontFace: fonts.display, fontSize: 74, bold: true, color: color.white },
        }),
        text("Cadence gives solo practitioners a calmer way to move from sessions delivered to invoices sent, payments tracked, and income ready to report.", {
          width: wrap(880),
          height: hug,
          style: { fontFace: fonts.body, fontSize: 30, color: "#DCE8FF" },
        }),
      ]),
      panel(
        {
          width: fill,
          height: fixed(560),
          padding: 36,
          fill: "#FFFFFF",
          borderRadius: 26,
        },
        column({ width: fill, height: fill, gap: 28, justify: "center" }, [
          text("Best-fit audience", { width: fill, height: hug, style: { fontFace: fonts.body, fontSize: 18, bold: true, color: color.orange } }),
          text("Educational therapists, tutors, academic coaches, and independent service providers who already schedule sessions in Outlook.", {
            width: fill,
            height: hug,
            style: { fontFace: fonts.display, fontSize: 38, bold: true, color: color.ink },
          }),
          rule({ width: fill, stroke: color.line, weight: 2 }),
          text("Primary CTA: schedule a short demo using one real billing month.", {
            width: fill,
            height: hug,
            style: { fontFace: fonts.body, fontSize: 26, color: color.slate },
          }),
        ]),
      ),
    ],
  ),
  color.navy,
);

const pptxBlob = await PresentationFile.exportPptx(presentation);
await pptxBlob.save(OUT);

for (let i = 0; i < presentation.slides.count; i += 1) {
  const slide = presentation.slides.getItem(i);
  const png = await presentation.export({ slide, format: "png", width: W, height: H });
  await writeFile(path.join(SCRATCH, `slide-${String(i + 1).padStart(2, "0")}.png`), Buffer.from(await png.arrayBuffer()));
}

const layout = await Promise.all(
  Array.from({ length: presentation.slides.count }, async (_, i) => {
    const slide = presentation.slides.getItem(i);
    return { slide: i + 1, layout: await slide.export({ format: "layout" }) };
  }),
);
await writeFile(
  path.join(SCRATCH, "layout.json"),
  JSON.stringify(layout, null, 2),
);

console.log(JSON.stringify({ pptx: OUT, slides: presentation.slides.count }, null, 2));
