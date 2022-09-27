using System;
using System.IO;
using System.Text;
using AppKit;
using Foundation;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Alert Raiser, provides alert facilities, among which methods to land the
    /// application softly.
    /// </summary>

    public static class AlertRaiser
    {
        #region Properties
        private static string ProgramName => Path.GetFileNameWithoutExtension(Environment.GetCommandLineArgs()[0]);
        private static string ErrorFile => Path.Combine(AppDelegate.DocumentsFolder, @"error.txt");
        private static string WarningFile => Path.Combine(AppDelegate.DocumentsFolder, @"warning.txt");
        #endregion

        #region Constructors
        static AlertRaiser()
        {
        }
        #endregion

        #region Public Methods
        public static void QuitWithAlert(string messageText, string informativeText)
        {
            var alert = new NSAlert()
            {
                AlertStyle = NSAlertStyle.Critical,
                MessageText = messageText,
                InformativeText = informativeText
            };
            alert.RunModal();
            NSApplication.SharedApplication.Terminate(NSApplication.SharedApplication);
        }

        public static void LandApplication(Exception ex)
        {
            WriteError(ex);
            RaiseAlert(ex);
            NSApplication.SharedApplication.Terminate(NSApplication.SharedApplication);
        }

        /// <summary>
        /// Stop the application after writing a stack dump on file and display
        /// an alert.
        /// If no alert can be displayed, raise a user notification.
        /// </summary>
        /// <param name="ex"></param>
        public static void RaiseAlert(Exception ex)
        {
            var alert = new NSAlert()
            {
                AlertStyle = NSAlertStyle.Critical,
                InformativeText = ex.ToString(),
                MessageText = $"Error in {ProgramName}."
            };
            alert.AddButton("Close");
            try
            {
                alert.RunModal();
            }
            catch (Exception ex2)
            {
                WriteError(ex, ex2);
                string title = $"Error in {ProgramName}";
                string text = $"See {ErrorFile}.";
                RaiseNotification(title, text);
            }
        }

        public static void RunInformationalAlert(string messageText, string informativeText, bool saveText=false)
        {
            var alert = new NSAlert()
            {
                AlertStyle = NSAlertStyle.Informational,
                MessageText = messageText,
                InformativeText = informativeText,
            };
            if (saveText)
            {
                alert.AddButton("OK");
                alert.AddButton("Save");
            }
            var result = alert.RunModal();

            // Save the text in the error file when the Save button is hit.
            if (result == 1001)
            {
                WriteWarning(informativeText);
                RaiseNotification("Alert text is saved", $"Text saved to {WarningFile}");
            }
        }

        public static bool RunDirtyWindowAlert(string messageText, string informativeText, Action saveAction)
        {
            // Create a critical alert.
            var alert = new NSAlert()
            {
                AlertStyle = NSAlertStyle.Critical,
                MessageText = messageText,
                InformativeText = informativeText,
            };
            alert.AddButton("Save");
            alert.AddButton("Cancel");

            // Run the alert.
            var result = alert.RunModal();

            // Take action based on result.
            switch (result)
            {
                case 1000:
                    // Save.
                    saveAction();
                    return true;
                case 1001:
                    // Cancel.
                    return false;
            }
            return false;
        }

        public static void WriteError(Exception ex, Exception ex2 = null)
        {
            WriteText(ErrorFile, ErrorString(ex, ex2));
        }

        public static void WriteWarning(string text)
        {
            WriteText(WarningFile, text);
        }

        public static void RaiseNotification(string title, string text)
        {
            // Trigger a local notification.
            // Configure the notification style in System Preferences.
            var notification = new NSUserNotification
            {
                Title = title,
                InformativeText = text,
                SoundName = NSUserNotification.NSUserNotificationDefaultSoundName,
                HasActionButton = false,
                HasReplyButton = false
            };
            NSUserNotificationCenter.DefaultUserNotificationCenter.DeliverNotification(notification);
        }
        #endregion

        #region Private Methods
        private static string ErrorString(Exception ex, Exception ex2 = null)
        {
            var builder = new StringBuilder();
            builder.AppendLine(DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"));
            builder.AppendLine();
            builder.AppendLine(ex.ToString());
            if (ex2 != null)
            {
                builder.AppendLine();
                builder.AppendLine(ex2.ToString());
            }
            return builder.ToString();
        }

        private static void WriteText(string file, string text)
        {
            System.IO.File.WriteAllText(file, text);
        }
        #endregion
    }
}
