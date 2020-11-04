using System;
using System.IO;
using System.Text;
using AppKit;
using Foundation;

namespace PresentScreenings.TableView
{
    static class MainClass
	{
        static string ProgramName => Path.GetFileNameWithoutExtension(Environment.GetCommandLineArgs()[0]);
        static string ErrorFile => Path.Combine(AppDelegate.DocumentsFolder, @"error.txt");

        static void Main(string[] args)
		{
            try
            {
                NSApplication.Init();
                NSApplication.Main(args);
            }
            catch (Exception ex)
            {
                WriteToErrorlog(ex);
                RaiseAlert(ex);
            }
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

        public static void WriteToErrorlog(Exception ex, Exception ex2 = null)
        {
            System.IO.File.WriteAllText(ErrorFile, ErrorString(ex, ex2));
        }

        public static void RaiseNotification(Exception ex)
        {
            // Trigger a local notification.
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
    }
}
