using System;
using System.Text;
using AppKit;
using AVFoundation;
using Foundation;

namespace PresentScreenings.TableView
{
    static class MainClass
	{
		static void Main(string[] args)
		{
            try
            {
                NSApplication.Init();
                NSApplication.Main(args);
            }
            catch (System.Exception ex)
            {
                var alert = new NSAlert()
                {
                    AlertStyle = NSAlertStyle.Critical,
                    InformativeText = ex.ToString(),
                    MessageText = "An error occurred"
                };
                try
                {
                    AlertWhenAlertCrashes(ex, ex);
                    alert.RunModal();
                }
                catch (System.Exception ex2)
                {
                    AlertWhenAlertCrashes(ex, ex2);
                }
            }
            NSApplication.SharedApplication.Terminate(NSApplication.SharedApplication);
		}

        public static void AlertWhenAlertCrashes(Exception ex, Exception ex2)
        {
            // Play a sound explaining the situation.
            string homeFolder = Environment.GetFolderPath(Environment.SpecialFolder.Personal);
            string soundFile = homeFolder + @"/Projects/FilmFestivalPlanner/Resources/Crash.mp3";
            var url = new NSUrl(soundFile);
            NSError error;
            var player = new AVAudioPlayer(url, "mp3", out error);
            player.Play();

            // Write the stack dump to a file.
            string errorFile = homeFolder + $"/Documents/Film/FilmFestivalPlanner.error.txt";
            var builder = new StringBuilder();
            builder.AppendLine(DateTime.Now.ToString());
            builder.AppendLine();
            if (error != null)
            {
                builder.AppendLine(error.ToString());
                builder.AppendLine();
            }
            builder.AppendLine(ex.ToString());
            builder.AppendLine();
            builder.AppendLine(ex2.ToString());
            System.IO.File.WriteAllText(errorFile, builder.ToString());
        }
    }
}
