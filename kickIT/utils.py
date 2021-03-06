import numpy as np
import pandas as pd
import scipy as sp
from scipy import integrate

import astropy.units as u
import astropy.constants as C

def interp_1d(xx, yy, **kwargs):
    kwargs.setdefault('kind', 'linear')
    kwargs.setdefault('bounds_error', False)
    kwargs.setdefault('fill_value', 0.0)

    interp = sp.interpolate.interp1d(xx, yy, **kwargs)
    return interp


def log_interp_1d(xx, yy, **kwargs):
    xx = np.log10(xx)
    yy = np.log10(yy)
    lin_interp = interp_1d(xx, yy, **kwargs)

    def interp(zz):
        zz = np.log10(zz)
        ww = lin_interp(zz)
        return np.power(10.0, ww)

    return interp


def annulus_areas(rads, relative=True, reset_inner=True):
    rr = rads
    if relative:
        rr = rr / rads[0]

    area = np.pi * (rr**2)
    area[1:] = area[1:] - area[:-1]
    # Assume log-distributed
    if reset_inner:
        area[0] = area[1]/(area[2]/area[1])

    return area


def shell_volumes(rads, relative=True, reset_inner=True):
    rr = rads
    if relative:
        rr = rr / rads[0]

    vol = (4.0/3.0)*np.pi * (rr**3)
    vol[1:] = vol[1:] - vol[:-1]
    # Assume log-distributed
    if reset_inner:
        vol[0] = vol[1]/(vol[2]/vol[1])

    return vol

def euler_rot(vectors, angles, axis):
    """
    Performed Euler angle transformation on vector.

    Takes in vectors as (Nsamples x Ndim)
    """
    if axis=='X':
        transformations = np.asarray([[[1,0,0],[0,np.cos(angle),-np.sin(angle)],[0,np.sin(angle),np.cos(angle)]] for angle in angles])
    elif axis=='Y':
        transformations = np.asarray([[[np.cos(angle),0,np.sin(angle)],[0,1,0],[-np.sin(angle),0,np.cos(angle)]] for angle in angles])
    elif axis=='Z':
        transformations = np.asarray([[[np.cos(angle),-np.sin(angle),0],[np.sin(angle),np.cos(angle),0],[0,0,1]] for angle in angles])
    else:
        raise ValueError("Unknown axis '{0:s}' specified in Euler transformation)".format(axis))

    rot_vectors = np.asarray([np.dot(trans,vector).T for (trans,vector) in zip(transformations, vectors)])
    return rot_vectors



def inspiral_time_peters(a0,e0,m1,m2,af=0):
    """
    Computes the inspiral time, in Gyr, for a binary
    a0 in Au, and masses in solar masses

    if different af is given, computes the time from a0,e0
    to that final semi-major axis

    for af=0, just returns inspiral time
    for af!=0, returns (t_insp,af,ef)
    """

    def deda_peters(a,e):
        num = 12*a*(1+(73./24)*e**2 + (37./96)*e**4)
        denom = 19*e*(1-e**2)*(1+(121./304)*e**2)
        return denom/num

    coef = 6.086768e-11 #G^3 / c^5 in au, gigayear, solar mass units
    beta = (64./5.) * coef * m1 * m2 * (m1+m2)

    if e0 == 0:
        if not af == 0:
            print("ERROR: doesn't work for circular binaries")
            return 0
        return a0**4 / (4*beta)

    c0 = a0 * (1.-e0**2.) * e0**(-12./19.) * (1.+(121./304.)*e0**2.)**(-870./2299.)

    if af == 0:
        eFinal = 0.
    else:
        r = ode(deda_peters)
        r.set_integrator('lsoda')
        r.set_initial_value(e0,a0)
        r.integrate(af)
        if not r.successful():
            print("ERROR, Integrator failed!")
        else:
            eFinal = r.y[0]

    time_integrand = lambda e: e**(29./19.)*(1.+(121./304.)*e**2.)**(1181./2299.) / (1.-e**2.)**1.5
    integral,abserr = integrate.quad(time_integrand,eFinal,e0)

    if af==0:
        return integral * (12./19.) * c0**4. / beta
    else:
        return (integral * (12./19.) * c0**4. / beta,af,eFinal)




def cartesian_to_cylindrical(x,y,z,vx,vy,vz):
    """
    Transforms positions and velocities from cartesian to cylindrical coordinates
    Takes in Astropy units
    """

    R = np.sqrt(x**2 + y**2).to(u.kpc)
    vR = ((x*vx + y*vy)/((x**2 + y**2)**(1./2))).to(u.km/u.s)

    Phi = np.arctan(y/x).to(u.rad)
    vPhi = ((x*vy - y*vx)/(x**2 + y**2)).to(1/u.s)

    Z = z.to(u.kpc)
    vZ = vz.to(u.km/u.s)

    return R,Phi,Z,vR,vPhi,vZ


def cylindrical_to_cartesian(R,Phi,Z,vR,vPhi,vZ):
    """
    Transforms positions and velocities from cylindrical to cartesian coordinates
    Takes in Astropy units
    """

    x = (R*np.cos(Phi)).to(u.kpc)
    vx = (vR*np.cos(Phi) - R*np.sin(Phi)*vPhi).to(u.km/u.s)

    y = (R*np.sin(Phi)).to(u.kpc)
    vy = (vR*np.sin(Phi) + R*np.cos(Phi)*vPhi).to(u.km/u.s)

    z = Z.to(u.kpc)
    vz = vZ.to(u.km/u.s)

    return x,y,z,vx,vy,vz



def Mphys_to_nat(M, ro=8*u.kpc, vo=220*u.km/u.s):
    """Converts physical masses to galpy natural units
    """
    M = M.to(u.kg)
    ro = ro.to(u.m)
    vo = vo.to(u.m/u.s)
    G = C.G.si

    Mo = vo**2 * ro / G

    return (M/Mo).value


def Mnat_to_phys(M, ro=8*u.kpc, vo=220*u.km/u.s):
    """Converts galpy natural units to physical masses
    """
    ro = ro.to(u.m)
    vo = vo.to(u.m/u.s)
    G = C.G.si

    Mo = vo**2 * ro / G

    return (M*Mo).to(Msun)


def Rphys_to_nat(r, ro=8*u.kpc, vo=220*u.km/u.s):
    """Converts physical distance to galpy natural units
    """

    return (r/ro).value


def Rnat_to_phys(r, ro=8*u.kpc, vo=220*u.km/u.s):
    """Converts galpy natural units to physical distance
    """

    return (r*ro).to(kpc)


def Tphys_to_nat(t, ro=8*u.kpc, vo=220*u.km/u.s):
    """Converts physical time to galpy natural units
    """
    ro = ro.to(km)

    to = ro/vo

    return (t/to).value


def Tnat_to_phys(t, ro=8*u.kpc, vo=220*u.km/u.s):
    """Converts galpy natural units to physical time
    """
    ro = ro.to(km)

    to = ro/vo

    return (t*to).to(Gyr)


def orbit_phys_to_nat(R, vR, vT, Z, vZ, Phi, ro=8*u.kpc, vo=220*u.km/u.s):
    """Converts orbital parameters from physical to natural units
    """

    R = R/ro
    vR = vR/vo
    vT = vT/vo
    Z = Z/ro
    vZ = vZ/vo
    Phi = Phi

    return R.value, vR.value, vT.value, Z.value, vZ.value, Phi.value


def orbit_nat_to_phys(R, vR, vT, Z, vZ, Phi, ro=8*u.kpc, vo=220*u.km/u.s):
    """Converts orbital parameters from natural units to physical
    """

    R = R*ro
    vR = vR*vo
    vT = vT*vo
    Z = Z*ro
    vZ = vZ*vo
    Phi = (Phi % (2*np.pi)) * u.rad

    return R, vR, vT, Z, vZ, Phi




# Functions for calculating functions with deviations from mean relations

def renumerate(arr):
    """Reverse Enumerate an array (with reversed indices also).
    """
    return zip(reversed(range(len(arr))), reversed(arr))


class Outlier():

    def __init__(self, xgrid, function=None, sgrid=None, ygrid=None, nmc=1e4, store=False):
        nmc = int(nmc)

        if function is None:
            function = self.function

        # Construct a grid of standard-deviation values
        if sgrid is None:
            SIGMA_GRID_RANGE = [-5.0, 5.0]   # standard-deviations
            SIGMA_GRID_SIZE = 50
            sgrid = np.linspace(*SIGMA_GRID_RANGE, SIGMA_GRID_SIZE)

        # Convert standard-deviations to percentiles
        sigma_percentiles = sp.stats.norm.cdf(sgrid)

        # Use the function to stochastically sample y-values
        #    shape: (N, M) for `N` x-vals, and `M` MC samples
        yvals_from_xgrid = function(xgrid[:, np.newaxis], size=nmc)

        # Calculate percentile-distributions of y-vals
        #    shape: (L, N) for `L` standard-deviation values and `N` (input) x-values
        yvals_percs = np.percentile(yvals_from_xgrid, 100*sigma_percentiles, axis=-1)

        # Construct grid of y-values
        if ygrid is None:
            # Find the range of valid y-values
            #    Min is the one reached by *highest* percentile, at lowest  x-value
            #    Max is the one reached by *lowest*  percentile, at highest x-value
            yvals_range = [np.max(yvals_percs[:, 0]), np.min(yvals_percs[:, -1])]
            ygrid = np.linspace(*yvals_range, xgrid.size+1)

        # Interpolate to find x-values corresponding to y-values at each percentile
        xvals_percs = [sp.interpolate.interp1d(pp, xgrid)(ygrid)
                       for pp in yvals_percs]

        if store:
            self._xgrid = xgrid
            self._ygrid = ygrid
            self._sgrid = sgrid
            self._xvals_percs = xvals_percs
            self._yvals_percs = yvals_percs

        # Construct 2D interpolants between values using standard deviations
        self._y_from_x_sigma = sp.interpolate.interp2d(xgrid, sgrid, yvals_percs)
        self._x_from_y_sigma = sp.interpolate.interp2d(ygrid, sgrid[::-1], xvals_percs)

        return

    @classmethod
    def function(cls, xx, size=None):
        raise NotImplementedError("Must be overridden in initialization or overwritten in subclass")

    def xs_to_y(self, xvals, sigma=0.0):
        yvals = self._y_from_x_sigma(xvals, sigma)
        return yvals

    def ys_to_x(self, yvals, sigma=0.0):
        xvals = self._x_from_y_sigma(yvals, sigma)
        return xvals


class OutlierND():

    def __init__(self, xgrids, function=None, sgrid=None, ygrid=None, nmc=1e4, store=False):
        nmc = int(nmc)

        if function is None:
            function = self.function

        # Construct a grid of standard-deviation values
        if sgrid is None:
            SIGMA_GRID_RANGE = [-5.0, 5.0]   # standard-deviations
            SIGMA_GRID_SIZE = 50
            sgrid = np.linspace(*SIGMA_GRID_RANGE, SIGMA_GRID_SIZE)

        # Convert standard-deviations to percentiles
        sigma_percentiles = sp.stats.norm.cdf(sgrid)

        # Create a meshgrid from the tuple of grids in each dimension
        mesh = np.meshgrid(*xgrids, indexing='ij')

        # Use the function to stochastically sample y-values
        #    shape: (N, M) for `N` x-vals, and `M` MC samples
        yvals_from_xgrid = function(*mesh, samples=nmc)
        # Calculate percentile-distributions of y-vals
        #    shape: (L, N) for `L` standard-deviation values and `N` (input) x-values
        yvals_percs = np.percentile(yvals_from_xgrid, 100*sigma_percentiles, axis=-1)
        yvals_percs = np.moveaxis(yvals_percs, 0, -1)

        # Construct grid of y-values
        if ygrid is None:
            # Find the range of valid y-values
            #    Min is the one reached by *highest* percentile, at lowest  x-value
            #    Max is the one reached by *lowest*  percentile, at highest x-value
            yvals_range = [np.max(yvals_percs[:, 0]), np.min(yvals_percs[:, -1])]
            ysize = np.max(np.shape(mesh)) + 1
            ygrid = np.linspace(*yvals_range, ysize)

        # Interpolate to find x-values corresponding to y-values at each percentile
        # xvals_percs = [sp.interpolate.interp1d(pp, xgrid)(ygrid)
        #                for pp in yvals_percs]

        if store:
            self._mesh = mesh
            self._ygrid = ygrid
            self._sgrid = sgrid
            self._yvals_percs = yvals_percs

        # Construct 2D interpolants between values using standard deviations
        args = tuple(xgrids) + (sgrid,)
        self._y_from_x_sigma = sp.interpolate.RegularGridInterpolator(
            args, yvals_percs, method='linear', bounds_error=True)
        # self._y_from_x_sigma = sp.interpolate.interp2d(xgrid, sgrid, yvals_percs)
        # self._x_from_y_sigma = sp.interpolate.interp2d(ygrid, sgrid[::-1], xvals_percs)

        return

    def __call__(self, *args, **kwargs):
        return self.xs_to_y(*args, **kwargs)

    @classmethod
    def function(cls, *xvals, samples=None):
        raise NotImplementedError("Must be overridden in initialization or overwritten in subclass")

    def xs_to_y(self, xvals, sigma=0.0):
        if np.isscalar(sigma):
            sigma = np.ones(np.shape(xvals)[0]) * sigma
        args = np.concatenate((xvals, sigma[:, np.newaxis]), axis=-1)
        yvals = self._y_from_x_sigma(args)
        return yvals

