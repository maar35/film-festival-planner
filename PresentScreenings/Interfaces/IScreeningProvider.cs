using System.Collections.Generic;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Screening provider. Delivers the current film and screening plus a
    /// screening list as seen from implementor's context.
    /// </summary>

    public interface IScreeningProvider
    {
        #region Properties
        Film CurrentFilm { get; }
        Screening CurrentScreening { get; }
        List<Screening> Screenings { get; }
        #endregion
    }
}
