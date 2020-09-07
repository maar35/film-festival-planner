using System;
using System.Collections.Generic;

namespace PresentScreenings.TableView
{
    public class UncombineTitlesEventArgs : EventArgs
    {
        #region Properties
        public readonly List<Screening> Screenings;
        #endregion

        #region Constructors
        public UncombineTitlesEventArgs(List<Screening> screenings)
        {
            Screenings = screenings;
        }
        #endregion
    }
}
