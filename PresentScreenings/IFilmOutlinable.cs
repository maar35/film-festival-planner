using System.Collections.Generic;
using AppKit;

namespace PresentScreenings.TableView
{
    public interface IFilmOutlinable
    {
        #region Properties
        List<IFilmOutlinable> FilmOutlinables { get; }
        #endregion

        #region Methods
        bool ContainsFilmOutlinables();
        void SetTitle(NSTextField view);
        void SetRating(NSTextField view);
        void SetGo(NSView view);
        void SetInfo(NSTextField view);
        #endregion
    }
}
