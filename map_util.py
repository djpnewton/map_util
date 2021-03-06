# -*- coding: utf-8 -*-
"""
Created on Wed Dec 07 14:08:33 2011

@author: OThane
"""

from tkFileDialog import *
import string
import re
from pylab import *


class map_t:
    # simple class to model a map file
    
    def __init__(self, mapf = None):
        # init class vars
        self._mapf = None
        self._symtbl = []
        self._comptbl = []
        self._ram_comptbl = []
        self._rom_comptbl = []        
        # load data
        if mapf != None:
            self.parse_map(mapf)
    
    def _parse_symtbl(self):
        pattern = re.compile('^\\s*(\\S*)\\s*(0x[0-9A-f]+)\\s{2,}(.*?)\\s{2,}(\\d+)\\s*(.*?\\.o).*')
        while 1:
            line = self._mapf.readline()
            if line == '' or line == '\n':
                break
            ret = pattern.findall(line)
            if len(ret) < 1:
                #print 'warning skipping line :' + line
                continue
            sym_line = ret[0]
            if len(sym_line) != 5:
                raise ValueError("unable to parse symbol ... " + line)
            sym_name = sym_line[0]
            sym_addr = int(sym_line[1], 16)
            sym_type = sym_line[2]
            sym_size = int(sym_line[3])
            sym_obj = sym_line[4]
            self._symtbl.append([sym_name, sym_addr, sym_type, sym_size, sym_obj])
    
    def _parse_comptbl(self):
        pattern = re.compile('^\\s+(\\d+)\\s+(\\d+)\\s+(\\d+)\\s+(\\d+)\\s+(\\d+)\\s+(\\d+)\\s+(.*?\\.o)')
        while 1:
            line = self._mapf.readline()
            if line == '' or line == '==============================================================================':
                break
            ret = pattern.findall(line)
            if len(ret) < 1:
                #print 'warning skipping line :' + line
                continue
            comp_line = ret[0]            
            if len(comp_line) != 7:
                raise ValueError("unable to parse symbol ... " + line)            
            code = int(comp_line[0])
            codata = int(comp_line[1])
            rodata = int(comp_line[2])
            rwdata = int(comp_line[3])
            zidata = int(comp_line[4])
            debug = int(comp_line[5])
            obj = comp_line[6]
            ram = rwdata + zidata
            rom = code + rodata + rwdata
            self._comptbl.append([ram, rom, code, codata, rodata, rwdata, zidata, debug, obj])
            self._ram_comptbl.append([ram, rwdata, zidata, obj])
            self._rom_comptbl.append([rom, code, codata, rodata, rwdata, obj])
            
    def _find_section(self, pattern):
        while 1:
            line = self._mapf.readline()
            if string.find(line, pattern) != -1 or line == '':
                break        
        if string.find(line, pattern) == -1:
            raise NameError('Can not find ' + pattern)

    def sort_symtbl_size(self):
        self._symtbl.sort(key = lambda l: l[3], reverse=True)

    def sort_ram_comptbl(self):
        self._ram_comptbl.sort(key = lambda l: l[0], reverse=True)
        
    def sort_rom_comptbl(self):
        self._rom_comptbl.sort(key = lambda l: l[0], reverse=True)

    def get_symtbl(self, obj=None):
        if obj == None:
            return self._symtbl
        else:
            # search for all symbols with this obj
            return [sym for sym in self._symtbl if sym[-1] == obj]
                    
    def get_ram_comptbl(self):
        return self._ram_comptbl
            
    def get_rom_comptbl(self):
        return self._rom_comptbl
            
    def hbar_ram(self, p = 1):
        # sort the ram here (perserve _ram_comptbl order so make new list)
        ram_sorted = sorted(self._ram_comptbl, key = lambda l: l[0], reverse=True)
        # build plotting arrays
        ram = []
        obj = []
        size = 0
        tot = 0
        for r in ram_sorted:
            tot += r[0]
        for r in ram_sorted:
            size += r[0]            
            ram.append(r[0])
            obj.append(r[-1])
            if size > tot * p:
                break
        N = len(ram)
        i = arange(N)
        barh(i, ram[0:N])
        title('RAM usage')
        xlabel('RAM (bytes)')
        yticks(i+0.2, obj[0:N])
        
    def hbar_rom(self, p = 1):
        # sort the rom here (perserve _rom_comptbl order so make new list)
        rom_sorted = sorted(self._rom_comptbl, key = lambda l: l[0], reverse=True)
        # build plotting arrays
        rom = []
        obj = []
        size = 0
        tot = 0
        for r in rom_sorted:
            tot += r[0]
        for r in rom_sorted:
            size += r[0]            
            rom.append(r[0])
            obj.append(r[-1])
            if size > tot * p:
                break
        N = len(rom)
        i = arange(N)
        barh(i, rom[0:N])
        title('ROM usage')
        xlabel('ROM (bytes)')
        yticks(i+0.2, obj[0:N])        
                
    def parse_map(self, mapf):
        """
        Parse the map file
        """        
        self._mapf = mapf
        
        # jump to Symbol Table Section (the first thing we are interested)
        self._find_section('Image Symbol Table')
        
        # jump to the local symbols and load them all
        self._find_section('    Local Symbols')
        self._mapf.readline()    
        self._mapf.readline()
        self._mapf.readline()
        self._parse_symtbl()
        
        # jump to the global symbols and load them all
        self._find_section('    Global Symbols')
        self._mapf.readline()
        self._mapf.readline()
        self._mapf.readline()
        self._parse_symtbl()
        
        # jump to the Image components
        self._find_section('Image component sizes')
        self._mapf.readline()
        self._mapf.readline()
        self._mapf.readline()
        self._mapf.readline()
        self._parse_comptbl()        


class _diff_tbl:
        # handles showing a diff table

        def __init__(self, diff_tbl, title = '', idx_size = 0, idx_name = -1, idx_type = None, on_obj_click = None):
            # ini class vars
            self._diff_tbl = diff_tbl
            self._title = title
            self._idx_size = idx_size
            self._idx_name = idx_name
            self._idx_type = idx_type
            self._figman = None
            self._barh = None
            self._ax = None
            self._difftbl_names = []
            self._on_obj_click = on_obj_click
        
        def __call__(self, event):
            if event.name == 'pick_event':
                # on pick event pop up a sorted symtbl for this obj
                if event.mouseevent.inaxes != self._ax: return
                i = int(event.mouseevent.ydata)
                obj = self._difftbl_names[i]
                if self._on_obj_click == None: return                
                self._on_obj_click(obj)
            
        def plot(self, ax, p = 1):
            self._ax = ax
            # sort the diff by size so display in an ordered way
            diff_sorted = sorted(self._diff_tbl, key = lambda l: l[self._idx_size], reverse=True)
            size = []
            names = []
            # get the total size so we can display p % of it
            tot_size = 0
            for r in diff_sorted:
                tot_size += abs(r[self._idx_size])
            # get p % of the list into names and sizes to plot
            cum_size = 0
            self._difftbl_names = []
            for r in diff_sorted:
                # accumulate size
                s = r[self._idx_size]
                cum_size += abs(s)
                size.append(abs(s))
                # format the name (a '*' indicates a negative value)
                name = ''
                if s < 0: name += '*'
                name += r[self._idx_name] 
                if self._idx_type != None: name += '(' + r[self._idx_type] + ')'
                names.append(name)
                self._difftbl_names.append(r[self._idx_name])
                # if we have we done p % of the total size the goto ploting
                if cum_size > tot_size * p:
                    break
            # plot the horizontal bar chart of all the sizes
            self._figman = get_current_fig_manager()
            i = arange(len(size))
            self._barh = barh(i, size, picker=50)
            title(self._title)
            xlabel('delta (bytes)')
            yticks(i+0.2, names)
            self._figman.canvas.mpl_connect('pick_event', self)


class map_diff_t:
    # handles diffing two map_t objs
    
    def __init__(self, map_a, map_b):
        # ini class vars
        self._ram_diffs = []
        self._ram_uniques = []
        self._rom_diffs = []
        self._rom_uniques = []
        # load data
        self._map_a = map_a
        self._map_b = map_b
        self._ram_diff()        
        self._rom_diff()
        
    def _ram_diff(self):
        # search for a in b
        for ram_a in self._map_a._ram_comptbl:
            found = False
            for ram_b in self._map_b._ram_comptbl:
                # if obj names are the same we found a in b
                if ram_a[-1] == ram_b[-1]: 
                    found = True
                    # if the size is the same then there is no diff
                    if ram_a[0] == ram_b[0]:
                        continue
                    # size is not the same so record the diff
                    delta = ram_b[0] - ram_a[0]
                    #if delta < 0:
                    #    delta = -delta
                    self._ram_diffs.append([delta, 'd', ram_a[-1]])
                    break
            if not found:
                # if we did not find a in b it is unique                
                self._ram_uniques.append([-ram_a[0], 'u', ram_a[-1]])
        # search for b in a
        for ram_b in self._map_b._ram_comptbl:
            found = False
            for ram_a in self._map_a._ram_comptbl:
                # if obj names are the same we found b in a
                if ram_b[-1] == ram_a[-1]:
                    # we already found these above so skip b
                    found = True
                    break
            if not found:
                # if we did not find b in a it is unique
                self._ram_uniques.append([ram_b[0], 'u', ram_b[-1]])
    
    def _rom_diff(self):
        # search for a in b
        for rom_a in self._map_a._rom_comptbl:
            found = False
            for rom_b in self._map_b._rom_comptbl:
                # if obj names are the same we found a in b
                if rom_a[-1] == rom_b[-1]: 
                    found = True
                    # if the size is the same then there is no diff
                    if rom_a[0] == rom_b[0]:
                        continue
                    # size is not the same so record the diff
                    delta = rom_b[0] - rom_a[0]
                    #if delta < 0:
                    #    delta = -delta
                    self._rom_diffs.append([delta, 'd', rom_a[-1]])
                    break
            if not found:
                # if we did not find a in b it is unique                
                self._rom_uniques.append([-rom_a[0], 'u', rom_a[-1]])
        # search for b in a
        for rom_b in self._map_b._rom_comptbl:
            found = False
            for rom_a in self._map_a._rom_comptbl:
                # if obj names are the same we found b in a
                if rom_b[-1] == rom_a[-1]:
                    # we already found these above so skip b
                    found = True
                    break
            if not found:
                # if we did not find b in a it is unique
                self._rom_uniques.append([rom_b[0], 'u', rom_b[-1]])        
    
    def _diff_symtbl(self, symtbl_a, symtbl_b):
        diff_symtbl = []
        # find a in b
        for sym_a in symtbl_a:
            found = False
            for sym_b in symtbl_b:
                if sym_a[0] == sym_b[0]:
                    # names are the same so they match
                    found = True
                    size_diff = sym_b[3] - sym_a[3]
                    if size_diff != 0:
                        # sizes differ so add to diff list
                        diff_symtbl.append([sym_a[0], 'd', size_diff])
            if found == False:
                # could not find a in b so a is unique
                diff_symtbl.append([sym_a[0], 'u', sym_a[3]])
        # find b in a
        for sym_b in symtbl_b:
            found = False
            for sym_a in symtbl_a:
                if sym_a[0] == sym_b[0]:
                    # names are the same so these have already been found above
                    found = True
                    break
            if found == False:
                # could not find b in a so b is unique
                diff_symtbl.append([sym_b[0], 'u', sym_b[3]])
        return diff_symtbl
    
    def hbar_symtbl(self, obj, p = 1):
        # get a list of diffs between symbols in map_a and map_b for obj
        symtbl = self._diff_symtbl(self._map_a.get_symtbl(obj), self._map_b.get_symtbl(obj))
        # sort the list
        symtbl.sort(key = lambda l: l[-1], reverse=True)
        # find out how much to plot
        tot_size = 0;
        for sym in symtbl:
            tot_size += abs(sym[-1])
        # get obj to plot
        cum_size = 0
        size = []
        names = []
        for sym in symtbl:
            cum_size += abs(sym[-1])
            size.append(abs(sym[-1]))
            # format the name (a '*' indicates a negative value)
            name = ''
            if sym[-1] < 0: name += '*'
            name += sym[0]
            name += '(' + sym[1] + ')'
            names.append(name)
            if cum_size > tot_size * p: break
        i = arange(len(size))
        figure()        
        barh(i, size)
        title('symbol table for ' + obj)
        xlabel('bytes')
        yticks(i+0.2, names)       
    
    def hbar_ram_diff(self, ax = None, p = 1):
        # just build one list of ram items that are unique or different sizes
        ram_diff_sorted = self._ram_diffs
        for unique in self._ram_uniques:
            ram_diff_sorted.append(unique)        
        # plot horizontal histogram
        diff_tbl = _diff_tbl(ram_diff_sorted, title = 'RAM diff', idx_type = 1, on_obj_click = self.hbar_symtbl)
        diff_tbl.plot(ax, p)
    
    def hbar_rom_diff(self, p = 1, ax = None):
        # just build one list of rom items that are unique or different sizes
        rom_diff_sorted = self._rom_diffs
        for unique in self._rom_uniques:
            rom_diff_sorted.append(unique)        
        # plot horizontal histogram
        diff_tbl = _diff_tbl(rom_diff_sorted, title = 'ROM diff', idx_type = 1, on_obj_click = self.hbar_symtbl)
        diff_tbl.plot(ax, p)
    
def anaylze():
    # get map file to parse
    filename = askopenfilename(title='load map file', filetypes = [('all', '.*'), ('map', '.map')])
    if filename:
        map = map_t(open(filename))
        # show rom and ram consumption 
        figure()
        subplot(131)
        map.hbar_rom(0.7)
        subplot(133)
        map.hbar_ram(0.7)
        show()

def compare():
    # get map files to parse
    filename1 = askopenfilename(title='load map file 1', filetypes = [('all', '.*'), ('map', '.map')])
    filename2 = askopenfilename(title='load map file 2', filetypes = [('all', '.*'), ('map', '.map')])
    if filename1 and filename2:
        map1 = map_t(open(filename1))
        map2 = map_t(open(filename2))
        # show memory delta between versions
        map_diff = map_diff_t(map1, map2)
        fig = figure()
        ax = fig.add_subplot(131)
        map_diff.hbar_ram_diff(ax=ax)
        ax = fig.add_subplot(133)
        map_diff.hbar_rom_diff(0.9, ax=ax)
        show()

import Tkinter
top = Tkinter.Tk()
top.title("Choose an option..")
button = Tkinter.Button(top, text="Analyze single map file", command=anaylze)
button.pack()
button = Tkinter.Button(top, text="Compare map files", command=compare)
button.pack()
Tkinter.mainloop()
