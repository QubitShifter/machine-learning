"use client";

import katex from "katex";

const katexOptions = {
  throwOnError: false,
  strict: "ignore" as const,
  trust: false,
  output: "htmlAndMathml" as const,
  displayMode: true,
};

const watermarkEquations = [
  {
    latex: "e^{i\\pi} + 1 = 0",
    placement: "equation-mark-euler",
  },
  {
    latex: "F = ma",
    placement: "equation-mark-force",
  },
  {
    latex: "E = mc^{2}",
    placement: "equation-mark-energy",
  },
  {
    latex: "\\int f(x)\\, dx",
    placement: "equation-mark-integral",
  },
  {
    latex: "y' + P(x)y = Q(x)",
    placement: "equation-mark-ode",
  },
  {
    latex: "\\nabla \\cdot E = \\rho / \\varepsilon_0",
    placement: "equation-mark-maxwell",
  },
  {
    latex: "(i\\gamma^{\\mu}\\partial_{\\mu} - m)\\psi = 0",
    placement: "equation-mark-dirac",
  },
  {
    latex:
      "R_{\\mu\\nu} - \\frac{1}{2}R g_{\\mu\\nu} + \\Lambda g_{\\mu\\nu} = \\frac{8\\pi G}{c^{4}}T_{\\mu\\nu}",
    placement: "equation-mark-einstein",
  },
  {
    latex: "\\begin{bmatrix} a & b \\\\ c & d \\end{bmatrix}",
    placement: "equation-mark-matrix",
  },
];

export function EquationShowcase() {
  return (
    <div
      aria-hidden="true"
      className="equation-showcase"
    >
      {watermarkEquations.map((equation) => (
        <span
          className={`equation-mark ${equation.placement}`}
          key={equation.placement}
          dangerouslySetInnerHTML={{
            __html: katex.renderToString(
              equation.latex,
              katexOptions,
            ),
          }}
        />
      ))}
    </div>
  );
}
