using System;
using System.Collections.Generic;

namespace PresentScreenings.TableView
{
    public class CombineTitlesEventArgs : EventArgs
    {
        #region Properties
        public readonly List<int> FilmIds;
        public readonly int MainFilmId;
        #endregion

        #region Constructors
        public CombineTitlesEventArgs(List<int> filmIds, int mainFilmId)
        {
            FilmIds = filmIds;
            MainFilmId = mainFilmId;
        }
        #endregion
    }
}
