# Security Model

## Modes

`APP_AUTH_ENABLED=false` is only for local classroom demos.

Production must set:

```text
APP_AUTH_ENABLED=true
APP_AUTH_SECRET=<long random secret>
APP_LOGIN_CODE=<operator login code>
```

This preserves compatibility with the current Vue frontend and its `sa-token` header.

## OIDC mode

For a real company identity provider, use:

```text
IDENTITY_PROVIDER=oidc
OIDC_ISSUER=https://issuer.example.com/
OIDC_AUDIENCE=crossborder-ops-agent
OIDC_JWKS_URL=https://issuer.example.com/.well-known/jwks.json
```

The backend validates JWT signatures through JWKS and checks issuer and audience.

## Remaining security work before real customer data

- Move secrets to the cloud provider's secret manager.
- Add role-based authorization checks per store and operator.
- Add audit logs for login, export, and admin actions.
- Add dependency vulnerability scanning in CI.
- Add backup, retention, and deletion policies for business data.
