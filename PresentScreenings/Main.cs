using System;
using System.IO;
using System.Text;
using AppKit;
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
            catch (Exception ex)
            {
                AlertRaiser.LandApplication(ex);
            }
        }
    }
}
