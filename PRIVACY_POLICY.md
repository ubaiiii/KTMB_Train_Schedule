# Privacy Policy

**Last Updated: August 8, 2026**

This privacy policy governs your use of the software application **KTMB Train Schedule** (referred to as the "App" or "Application"), created by **Bayu  Tech** (referred to as "we", "us", or "our"). 

The Application provides KTM Komuter train timetables, simulated journey trackers, offboarding proximity alarms (warning alerts before arrival), and crowdsourced delay reporting to help commuters estimate train delays.

---

## 1. Information We Collect and How It Is Used

### A. Location Data (GPS)
The App requires access to your device's geographical location coordinates (GPS) to provide its core features:
* **Offboarding Proximity Alarms**: The App monitors your location relative to your destination station to trigger warning notifications and sound alerts when you are approaching. This may require accessing location data in the background (when the app is minimized or the screen is locked).
* **Crowdsourced Delay Verification**: When you submit a train delay report, the App captures your current latitude and longitude to verify that the report is submitted from the vicinity of the relevant train station (GPS verification).

### B. Device and Connection Information
* **Headphone Connection State**: The App checks whether headphones (earphones, headsets, or Bluetooth audio devices) are connected to your device. This is used solely to route the alarm sound safely to your headphones (avoiding public disturbance) according to your preferences.
* **Storage (AsyncStorage)**: The App stores schedule tables, custom alarm configurations, and a local history of your logged journeys on your device's local storage.

### C. Public Delay Reports
* When you report a train delay, the following data is transmitted to our secure cloud database (hosted on Supabase) and shared publicly with other App users:
  * Date and Train ID (Service ID)
  * Departure and Destination Stations
  * Scheduled Arrival Time and Actual Arrival Time
  * Calculated delay duration (in minutes)
  * Reporter coordinates (latitude and longitude) for verification
* **No personally identifiable information (PII) such as your name, email address, phone number, contacts, or account credentials is collected, saved, or transmitted.**

---

## 2. Device Permissions Required

To function correctly, the App will request your permission to access the following native device features:
* **Location Services (`ACCESS_FINE_LOCATION`, `ACCESS_COARSE_LOCATION`)**: Required to track your position along the transit line.
* **Background Location (`ACCESS_BACKGROUND_LOCATION`)**: Required to continue tracking your distance and fire the offboarding alert even when your device screen is locked or idle.
* **Notifications (`POST_NOTIFICATIONS`)**: Required to display alarm warnings, countdowns, and heads-up SMS-style arrival popups on your screen.
* **Vibrate (`VIBRATE`)**: Used to trigger physical device vibration during alerts.
* **Internet access (`INTERNET`)**: Required to fetch latest train timetables and upload crowdsourced delay statistics.

---

## 3. Data Retention and Sharing
* **Local Data**: Your local settings and local journey history are stored on your device and can be cleared at any time by clearing the App's storage cache in your system settings.
* **Cloud Data**: Public delay reports submitted to our database do not contain any personal data. We do not sell, rent, or share any of this verified transit delay information with third-party advertisers.

---

## 4. Children's Privacy
The Application does not address anyone under the age of 13. We do not knowingly collect personal identifiable information from children. If we discover that a child under 13 has provided us with personal information, we immediately delete this from our servers.

---

## 5. Changes to This Privacy Policy
We may update our Privacy Policy from time to time. You are advised to review this page periodically for any changes. We will notify you of any changes by posting the new Privacy Policy on this page.

---

## 6. Contact Us
If you have any questions or suggestions about this Privacy Policy, do not hesitate to contact us at:
* **Email**: ubaiiii@gmail.com  
* **GitHub**: https://github.com/ubaiiii 
