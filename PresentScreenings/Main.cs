using System;
using AppKit;

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
