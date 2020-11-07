using System;
using System.IO;
using System.Text;
using AppKit;
using Foundation;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Alert Raiser, stops the application after writing a stack dump on file
    /// and displaying an alert.
    /// If no alert can be displayed, a usrr notification is raised.
    /// </summary>
    public static class AlertRaiser
    {
        #region Properties
        static string ProgramName => Path.GetFileNameWithoutExtension(Environment.GetCommandLineArgs()[0]);
        static string ErrorFile => Path.Combine(AppDelegate.DocumentsFolder, @"error.txt");
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
            WriteToErrorlog(ex);
            RaiseAlert(ex);
            NSApplication.SharedApplication.Terminate(NSApplication.SharedApplication);
        }

        public static void RaiseAlert(Exception ex)
        {
            var alert = new NSAlert()
            {
                AlertStyle = NSAlertStyle.Critical,
                InformativeText = ex.ToString(),
                MessageText = $"Error in {ProgramName}."
            };
            try
            {
                alert.RunModal();
            }
            catch (Exception ex2)
            {
                WriteToErrorlog(ex, ex2);
                RaiseNotification(ex);
            }
        }

        public static void RunInformationalAlert(string messageText, string informativeText)
        {
            var alert = new NSAlert()
            {
                AlertStyle = NSAlertStyle.Informational,
                MessageText = messageText,
                InformativeText = informativeText
            };
            alert.RunModal();
        }

        public static void WriteToErrorlog(Exception ex, Exception ex2 = null)
        {
            System.IO.File.WriteAllText(ErrorFile, ErrorString(ex, ex2));
        }

        public static void RaiseNotification(Exception ex)
        {
            // Trigger a local notification.
            // Configure the notification style in System Preferences.
            var notification = new NSUserNotification
            {
                Title = $"Error in {ProgramName}.",
                InformativeText = $"See {ErrorFile}.",
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
        #endregion
    }
}
