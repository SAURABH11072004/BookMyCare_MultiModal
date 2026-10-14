import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../lib/auth";
import { LoginPage } from "../pages/Auth";
import { ResultView } from "../pages/AnalysisResult";
import { analysisFixture } from "./fixtures";

afterEach(() => vi.unstubAllGlobals());

describe("ResultView", () => {
  it("shows urgency, red flags, conditions with explanations and the mock label", async () => {
    render(<MemoryRouter><ResultView result={analysisFixture} /></MemoryRouter>);
    expect(screen.getByTestId("urgency-banner")).toHaveTextContent("See a doctor within 24 hours.");
    expect(screen.getByText("Warning signs detected")).toBeInTheDocument();
    expect(screen.getByText("Dengue fever")).toBeInTheDocument();
    expect(screen.getByText("86%")).toBeInTheDocument();
    expect(screen.getByText("Mock AI")).toBeInTheDocument();
    // top condition is expanded by default and shows its factors, including evidence against
    expect(screen.getByText("Why this was suggested")).toBeInTheDocument();
    expect(screen.getByText(/HbA1c normal/)).toBeInTheDocument();
    expect(screen.getByText(/not a medical diagnosis/)).toBeInTheDocument();
    // collapsing works
    await userEvent.click(screen.getByRole("button", { expanded: true }));
    expect(screen.queryByText("Why this was suggested")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Read on who.int/ })).toHaveAttribute("href", "https://www.who.int/x");
  });
});

describe("LoginPage", () => {
  it("shows the server error message on failed login", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detail: "Incorrect email or password" }), { status: 401 })));
    render(<MemoryRouter><AuthProvider><LoginPage /></AuthProvider></MemoryRouter>);
    await userEvent.type(screen.getByLabelText("Email"), "a@b.com");
    await userEvent.type(screen.getByLabelText("Password"), "wrongpass1");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Incorrect email or password"));
  });

  it("reports a friendly message when the backend is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("Failed to fetch"); }));
    render(<MemoryRouter><AuthProvider><LoginPage /></AuthProvider></MemoryRouter>);
    await userEvent.type(screen.getByLabelText("Email"), "a@b.com");
    await userEvent.type(screen.getByLabelText("Password"), "Password1");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/Cannot reach the BookMyCare server/));
  });
});
