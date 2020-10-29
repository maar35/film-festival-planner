using System;
using AppKit;
using AudioToolbox;

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
                    MessageText = "An error occurred",
                };
                try
                {
                    alert.RunModal();
                }
                catch (System.Exception)
                {
                    string homeFolder = Environment.GetFolderPath(Environment.SpecialFolder.Personal);
                    string errorFile = homeFolder + $"/Documents/Film/FilmFestivalPlanner.error.txt";
                    System.IO.File.WriteAllText(errorFile, DateTime.Now.ToString() + "\n" + alert.InformativeText);
                }
                NSApplication.SharedApplication.Terminate(NSApplication.SharedApplication);
            }
		}
	}
}
