# A2 MESS HUB — Cloudinary Bill Photo Storage

Production PWA bill-photo uploads use Cloudinary unsigned uploads.

- Cloud name: `rtsrjhpm`
- Unsigned upload preset: `a2_mess_bills`
- Folder: `A2-MESS-HUB/Bills`
- Upload endpoint: `https://api.cloudinary.com/v1_1/rtsrjhpm/image/upload`

Security notes:

- Never commit a Cloudinary API Secret.
- Browser/mobile clients only use the cloud name and unsigned upload preset.
- Existing Uploadcare URLs remain valid for historical expense records.
- New expense photo uploads are stored in Cloudinary and the returned HTTPS URL is stored in Firestore.
