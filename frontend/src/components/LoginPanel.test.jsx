import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LoginPanel from "./LoginPanel";
import { apiClient, ApiError } from "../api/client";

const authState = {
  login: vi.fn(),
  refreshUser: vi.fn(),
};

vi.mock("../context/AuthContext", () => ({
  useAuth: () => authState,
}));

vi.mock("../api/client", async () => {
  const actual = await vi.importActual("../api/client");
  return {
    ...actual,
    apiClient: {
      ...actual.apiClient,
      getAuthBootstrapStatus: vi.fn(),
      bootstrapAdmin: vi.fn(),
    },
  };
});

describe("LoginPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiClient.getAuthBootstrapStatus.mockResolvedValue({
      setup_required: false,
    });
  });

  it("connects with existing admin credentials", async () => {
    authState.login.mockResolvedValue({ username: "admin" });
    render(<LoginPanel />);

    await waitFor(() =>
      expect(apiClient.getAuthBootstrapStatus).toHaveBeenCalled()
    );

    await userEvent.type(
      screen.getByLabelText("Nom d'utilisateur"),
      "admin"
    );
    await userEvent.type(screen.getByLabelText("Mot de passe"), "secret123");
    await userEvent.click(screen.getByRole("button", { name: "Se connecter" }));

    await waitFor(() =>
      expect(authState.login).toHaveBeenCalledWith("admin", "secret123")
    );
    expect(authState.refreshUser).not.toHaveBeenCalled();
  });

  it("bootsraps the first admin when setup is required", async () => {
    apiClient.getAuthBootstrapStatus.mockResolvedValue({
      setup_required: true,
    });
    apiClient.bootstrapAdmin.mockResolvedValue({
      access_token: "token",
      token_type: "bearer",
    });
    authState.refreshUser.mockResolvedValue({ username: "rootadmin" });

    render(<LoginPanel />);

    await waitFor(() =>
      expect(
        screen.getByRole("heading", {
          name: "Creation du premier administrateur",
        })
      ).toBeInTheDocument()
    );

    await userEvent.type(
      screen.getByLabelText("Nom d'utilisateur"),
      "rootadmin"
    );
    await userEvent.type(
      screen.getByLabelText("Mot de passe"),
      "motdepasse-fort"
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Creer le compte admin" })
    );

    await waitFor(() =>
      expect(apiClient.bootstrapAdmin).toHaveBeenCalledWith({
        username: "rootadmin",
        password: "motdepasse-fort",
      })
    );
    expect(authState.refreshUser).toHaveBeenCalled();
  });

  it("switches to bootstrap mode when backend auth is not configured", async () => {
    authState.login.mockRejectedValue(
      new ApiError(503, "Aucun compte admin configure")
    );
    render(<LoginPanel />);

    await waitFor(() =>
      expect(apiClient.getAuthBootstrapStatus).toHaveBeenCalled()
    );

    await userEvent.type(
      screen.getByLabelText("Nom d'utilisateur"),
      "admin"
    );
    await userEvent.type(screen.getByLabelText("Mot de passe"), "secret123");
    await userEvent.click(screen.getByRole("button", { name: "Se connecter" }));

    await waitFor(() =>
      expect(
        screen.getByText(
          "Authentification non configuree sur le backend. Creez le premier compte admin."
        )
      ).toBeInTheDocument()
    );
    expect(
      screen.getByRole("heading", {
        name: "Creation du premier administrateur",
      })
    ).toBeInTheDocument();
  });
});
