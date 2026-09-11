# A2 MESS HUB — Cloudinary Bill Photo Storage

Production bill-photo uploads use Cloudinary unsigned uploads.

- Cloud name: `rtsrjhpm`
- Unsigned upload preset: `a2_mess_bills`
- Folder: `A2-MESS-HUB/Bills`
- Upload endpoint: `https://api.cloudinary.com/v1_1/rtsrjhpm/image/upload`

Behavior:

- New expense bill photos upload to Cloudinary.
- The returned secure HTTPS URL and Cloudinary public ID are stored in Firestore.
- Existing Uploadcare URLs remain readable for historical expense records.
- PWA and future stable APK builds use the same Cloudinary upload configuration.

Security notes:

- Never commit a Cloudinary API Secret.
- Browser/mobile clients only use the cloud name and unsigned upload preset.
