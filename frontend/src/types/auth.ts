export type AuthUser = {
  id: string;
  external_id: string;
  username?: string | null;
  email?: string | null;
  display_name?: string | null;
  is_admin?: boolean;
};

export type AuthTokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
};
