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
        public static string WarningFile => Path.Combine(AppDelegate.DocumentsFolder, @"warning.txt");
        public static string InfoFile => Path.Combine(AppDelegate.DocumentsFolder, @"info.txt");
        private static int AlertDepth { get; set; }
        #endregion

        #region Constructors
        static AlertRaiser()
        {
            AlertDepth = 0;
        }
        #endregion

        #region Public Methods
        public static void QuitWithAlert(string messageText, string informativeText)
        {
            _ = RunCriticalAlert(messageText, informativeText);
            TerminateApp();
        }

        public static void LandApplication(Exception ex)
        {
            WriteError(ex);
            RaiseAlert(ex);
            TerminateApp();
        }

        public static void RaiseAlert(Exception ex)
        {
            _ = RunCriticalAlert($"Error in {ProgramName}", ex.ToString());
        }

        public static nint RunCriticalAlert(string messageText, string informativeText)
        {
            var alert = new NSAlert()
            {
                AlertStyle = NSAlertStyle.Critical,
                InformativeText = informativeText,
                MessageText = messageText,
            };
            alert.AddButton("Close");
            return RunAlertAsModal(alert);
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
            var result = RunAlertAsModal(alert);

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
            var result = RunAlertAsModal(alert);

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

        public static void WriteInfo(string text)
        {
            WriteText(InfoFile, text);
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
        private static nint RunAlertAsModal(NSAlert alert)
        {
            AlertDepth += 1;
            nint alertResult = 0;
            try
            {
                alertResult = alert.RunModal();
            }
            catch (Exception ex)
            {
                HandleFailedAlertRun(ex.Message, alert);
            }
            if (alertResult < 0)
            {
                HandleFailedAlertRun($"Alert returned {alertResult}.", alert);
            }
            AlertDepth -= 1;
            return alertResult;
        }

        private static void HandleFailedAlertRun(string newErrorTitle, NSAlert alert)
        {
            if (AlertDepth > 1)
            {
                return;
            }
            var builder = new StringBuilder();
            builder.AppendLine($"Original critical error:");
            builder.AppendLine(alert.MessageText);
            builder.AppendLine(alert.InformativeText);
            var text = builder.ToString();
            RaiseNotification(newErrorTitle, text);
            throw new AlertReturnsNonZeroValue($"{newErrorTitle}{Environment.NewLine}{text}");
        }

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

        private static void TerminateApp()
        {
            NSApplication.SharedApplication.Terminate(NSApplication.SharedApplication);
        }
        #endregion
    }
}
